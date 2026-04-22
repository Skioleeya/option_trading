use pyo3::exceptions::PyRuntimeError;
use pyo3::prelude::*;
use pyo3::types::PyDict;
use std::collections::{HashMap, VecDeque};
use std::thread::sleep;
use std::time::{Duration, Instant, SystemTime, UNIX_EPOCH};

fn now_secs() -> f64 {
    SystemTime::now().duration_since(UNIX_EPOCH).map(|d| d.as_secs_f64()).unwrap_or(0.0)
}

#[pyclass(frozen, module = "shared_rust.services_l0_support")]
pub struct RequestPriority;
#[pymethods]
impl RequestPriority {
    #[classattr]
    pub const QUOTE: i32 = 0;
    #[classattr]
    pub const OI: i32 = 1;
    #[classattr]
    pub const HISTORY: i32 = 2;
    #[classattr]
    pub const SYSTEM: i32 = 3;
}

struct TokenBucket {
    rate: f64,
    burst: usize,
    tokens: f64,
    last_refill: Instant,
}
impl TokenBucket {
    fn new(rate: f64, burst: usize) -> Self {
        Self { rate, burst, tokens: burst as f64, last_refill: Instant::now() }
    }
    fn refill(&mut self) {
        let now = Instant::now();
        let elapsed = now.duration_since(self.last_refill).as_secs_f64();
        self.tokens = (self.tokens + elapsed * self.rate).min(self.burst as f64);
        self.last_refill = now;
    }
    fn wait_for_token(&mut self) {
        loop {
            self.refill();
            if self.tokens >= 1.0 {
                self.tokens -= 1.0;
                return;
            }
            let sleep_s = if self.rate > 0.0 { 1.0 / self.rate } else { 0.05 };
            sleep(Duration::from_secs_f64(sleep_s));
        }
    }
}

struct SlidingWindow {
    limit: usize,
    window_s: f64,
    timestamps: VecDeque<Instant>,
}
impl SlidingWindow {
    fn new(limit: usize, window_s: f64) -> Self { Self { limit, window_s, timestamps: VecDeque::new() } }
    fn wait(&mut self) {
        loop {
            let now = Instant::now();
            let cutoff = now.checked_sub(Duration::from_secs_f64(self.window_s)).unwrap_or(now);
            while let Some(front) = self.timestamps.front() {
                if *front < cutoff { self.timestamps.pop_front(); } else { break; }
            }
            if self.timestamps.len() < self.limit {
                self.timestamps.push_back(now);
                return;
            }
            sleep(Duration::from_millis(50));
        }
    }
}

struct CircuitBreaker {
    consecutive_fails: usize,
    reset_s: f64,
    fails: usize,
    open_until: Option<Instant>,
}
impl CircuitBreaker {
    fn new(consecutive_fails: usize, reset_s: f64) -> Self { Self { consecutive_fails, reset_s, fails: 0, open_until: None } }
    fn is_open(&self) -> bool { self.open_until.map(|x| Instant::now() < x).unwrap_or(false) }
    fn record_success(&mut self) { self.fails = 0; }
    fn record_failure(&mut self) {
        self.fails += 1;
        if self.fails >= self.consecutive_fails {
            self.open_until = Some(Instant::now() + Duration::from_secs_f64(self.reset_s));
            self.fails = 0;
        }
    }
}

#[pyclass(module = "shared_rust.services_l0_support")]
pub struct AdaptiveRateGovernor {
    bucket: std::sync::Mutex<TokenBucket>,
    endpoint_limit: usize,
    windows: std::sync::Mutex<HashMap<String, SlidingWindow>>,
    breaker: std::sync::Mutex<CircuitBreaker>,
    latencies: std::sync::Mutex<VecDeque<f64>>,
    rejected: std::sync::atomic::AtomicUsize,
}

#[pyclass(module = "shared_rust.services_l0_support")]
pub struct GovernorPermit {
    governor: Py<AdaptiveRateGovernor>,
    endpoint: String,
    priority: i32,
    entered: bool,
}

#[pymethods]
impl GovernorPermit {
    fn __enter__(mut slf: PyRefMut<'_, Self>, py: Python<'_>) -> PyResult<Py<Self>> {
        let governor = slf.governor.bind(py).borrow();
        {
            let breaker = governor.breaker.lock().map_err(|_| PyRuntimeError::new_err("Circuit breaker state poisoned"))?;
            if breaker.is_open() {
                governor.rejected.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                return Err(PyRuntimeError::new_err("Circuit breaker is open — request rejected"));
            }
        }
        let start = Instant::now();
        governor.bucket.lock().map_err(|_| PyRuntimeError::new_err("Token bucket poisoned"))?.wait_for_token();
        {
            let mut windows = governor.windows.lock().map_err(|_| PyRuntimeError::new_err("Sliding window state poisoned"))?;
            windows.entry(slf.endpoint.clone()).or_insert_with(|| SlidingWindow::new(governor.endpoint_limit, 1.0)).wait();
        }
        governor.latencies.lock().map_err(|_| PyRuntimeError::new_err("Latency store poisoned"))?.push_back(start.elapsed().as_secs_f64() * 1000.0);
        slf.entered = true;
        Ok(slf.into())
    }
    #[pyo3(signature = (exc_type=None, exc=None, _tb=None))]
    fn __exit__(&mut self, py: Python<'_>, exc_type: Option<&Bound<'_, PyAny>>, exc: Option<&Bound<'_, PyAny>>, _tb: Option<&Bound<'_, PyAny>>) -> PyResult<bool> {
        let governor = self.governor.bind(py).borrow();
        let mut breaker = governor.breaker.lock().map_err(|_| PyRuntimeError::new_err("Circuit breaker state poisoned"))?;
        if let Some(exc) = exc {
            let msg = exc.str()?.to_str()?.to_lowercase();
            if msg.contains("429") || msg.contains("rate limit") { breaker.record_failure(); }
        } else if exc_type.is_none() {
            breaker.record_success();
        }
        Ok(false)
    }
    fn endpoint(&self) -> String { self.endpoint.clone() }
    fn priority(&self) -> i32 { self.priority }
}

#[pymethods]
impl AdaptiveRateGovernor {
    #[new]
    #[pyo3(signature = (rate_per_s=8.0, burst=8, endpoint_limit=5, breaker_fails=3, breaker_reset_s=30.0))]
    fn new(rate_per_s: f64, burst: usize, endpoint_limit: usize, breaker_fails: usize, breaker_reset_s: f64) -> Self {
        Self {
            bucket: std::sync::Mutex::new(TokenBucket::new(rate_per_s, burst)),
            endpoint_limit,
            windows: std::sync::Mutex::new(HashMap::new()),
            breaker: std::sync::Mutex::new(CircuitBreaker::new(breaker_fails, breaker_reset_s)),
            latencies: std::sync::Mutex::new(VecDeque::with_capacity(1000)),
            rejected: std::sync::atomic::AtomicUsize::new(0),
        }
    }
    #[pyo3(signature = (endpoint="default", priority=RequestPriority::OI))]
    fn acquire(slf: Py<Self>, endpoint: &str, priority: i32) -> GovernorPermit {
        GovernorPermit { governor: slf, endpoint: endpoint.to_string(), priority, entered: false }
    }
    fn record_429(&self) -> PyResult<()> {
        self.breaker.lock().map_err(|_| PyRuntimeError::new_err("Circuit breaker state poisoned"))?.record_failure();
        Ok(())
    }
    fn metrics(&self, py: Python<'_>) -> PyResult<Py<PyDict>> {
        let latencies = self.latencies.lock().map_err(|_| PyRuntimeError::new_err("Latency store poisoned"))?;
        let mut lats = latencies.iter().copied().collect::<Vec<_>>();
        lats.sort_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));
        let n = lats.len();
        let p50 = if n == 0 { 0.0 } else { lats[((0.50 * n as f64) as usize).min(n - 1)] };
        let p99 = if n == 0 { 0.0 } else { lats[((0.99 * n as f64) as usize).min(n - 1)] };
        let d = PyDict::new(py);
        d.set_item("p50_wait_ms", p50)?;
        d.set_item("p99_wait_ms", p99)?;
        d.set_item("token_bucket_tokens", self.bucket.lock().map_err(|_| PyRuntimeError::new_err("Token bucket poisoned"))?.tokens)?;
        d.set_item("rejected_total", self.rejected.load(std::sync::atomic::Ordering::Relaxed))?;
        d.set_item("breaker_open", self.breaker.lock().map_err(|_| PyRuntimeError::new_err("Circuit breaker state poisoned"))?.is_open() as i32 as f64)?;
        Ok(d.unbind())
    }
}

#[pyclass(module = "shared_rust.services_l0_support")]
pub struct PrioritizedRequest {
    #[pyo3(get)] pub priority: i32,
    #[pyo3(get)] pub seq: i64,
    #[pyo3(get)] pub created_at: f64,
    #[pyo3(get)] pub endpoint: String,
    #[pyo3(get)] pub payload: Option<Py<PyAny>>,
}
#[pymethods]
impl PrioritizedRequest {
    fn wait_ms(&self) -> f64 { (now_secs() - self.created_at) * 1000.0 }
}

#[pyclass(module = "shared_rust.services_l0_support")]
pub struct PriorityRequestQueue {
    maxsize: usize,
    seq: i64,
    queue: VecDeque<PrioritizedRequest>,
    rejected: usize,
}
#[pymethods]
impl PriorityRequestQueue {
    #[new]
    #[pyo3(signature = (maxsize=256))]
    fn new(maxsize: usize) -> Self { Self { maxsize, seq: 0, queue: VecDeque::new(), rejected: 0 } }
    #[pyo3(signature = (endpoint, payload=None, priority=RequestPriority::HISTORY))]
    fn put(&mut self, endpoint: &str, payload: Option<Py<PyAny>>, priority: i32) -> bool {
        if self.queue.len() >= self.maxsize { self.rejected += 1; return false; }
        self.seq += 1;
        let req = PrioritizedRequest { priority, seq: self.seq, created_at: now_secs(), endpoint: endpoint.to_string(), payload };
        let idx = self.queue.iter().position(|x| x.priority > req.priority || (x.priority == req.priority && x.seq > req.seq)).unwrap_or(self.queue.len());
        self.queue.insert(idx, req);
        true
    }
    #[pyo3(signature = (timeout=None))]
    fn get(&mut self, timeout: Option<f64>) -> Option<PrioritizedRequest> {
        if self.queue.is_empty() {
            if let Some(timeout) = timeout { sleep(Duration::from_secs_f64(timeout)); }
        }
        self.queue.pop_front()
    }
    fn task_done(&self) {}
    #[getter]
    fn qsize(&self) -> usize { self.queue.len() }
    #[getter]
    fn rejected_count(&self) -> usize { self.rejected }
}

pub fn register(_py: Python<'_>, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<RequestPriority>()?;
    m.add_class::<AdaptiveRateGovernor>()?;
    m.add_class::<GovernorPermit>()?;
    m.add_class::<PrioritizedRequest>()?;
    m.add_class::<PriorityRequestQueue>()?;
    Ok(())
}
