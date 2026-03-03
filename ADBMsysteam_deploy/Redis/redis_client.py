"""
美股广度监控系统 - Redis客户端连接池优化版
实现单例模式、高性能连接池、重试机制和批量操作优化
"""

import logging
import redis
import time
import os
from typing import Optional, Any, Dict, List
from datetime import datetime
from zoneinfo import ZoneInfo
import threading
import json
try:
    from .settings import validate_configuration
except ImportError:
    # 当作为独立脚本运行时使用绝对导入
    from settings import validate_configuration

# US Eastern Time zone - 符合Python 3.13现代语法
ET = ZoneInfo("America/New_York")


class RedisClient:
    """
    Redis客户端 - 连接池优化版
    实现单例模式、高性能连接池、重试机制和批量操作优化
    """

    # 单例模式实现
    _instance: Optional['RedisClient'] = None
    _lock = threading.Lock()

    # 连接池配置常量
    CONNECTION_POOL_CONFIG = {
        'max_connections': 20,      # 最大连接数
        'decode_responses': True,  # 返回字符串而非字节
        'socket_connect_timeout': 10,  # 连接超时10秒
        'socket_timeout': 10,       # 读写超时10秒
        'socket_keepalive': True,   # 启用keepalive
        # Note: socket_keepalive_options removed - not supported on all systems
        # This was causing "Error 22: Invalid argument" on some platforms
    }

    # Redis客户端配置常量 - 支持环境变量配置
    CLIENT_CONFIG = {
        'health_check_interval': int(os.getenv('REDIS_HEALTH_CHECK_INTERVAL', '30')),  # 健康检查间隔(秒)
        'retry_on_timeout': True,    # 超时重试
        'max_retries': int(os.getenv('REDIS_MAX_RETRIES', '3')),           # 最大重试次数
        'retry_delay': float(os.getenv('REDIS_RETRY_DELAY', '0.1')),          # 重试延迟(秒)
        'connection_timeout': int(os.getenv('REDIS_CONNECTION_TIMEOUT', '5')),  # 连接超时(秒)
        'max_connection_errors': int(os.getenv('REDIS_MAX_CONNECTION_ERRORS', '5')),  # 最大连续错误次数
        'exponential_backoff_base': float(os.getenv('REDIS_BACKOFF_BASE', '2.0')),  # 指数退避基数
        'max_retry_delay': float(os.getenv('REDIS_MAX_RETRY_DELAY', '30.0')),  # 最大重试延迟(秒)
    }

    def __new__(cls, host: str = "localhost", port: int = 6379,
                 password: str | None = None, db: int = 0) -> 'RedisClient':
        """单例模式实现"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, host: str = "localhost", port: int = 6379,
                 password: str | None = None, db: int = 0, validate_config: bool = True):
        """初始化Redis客户端

        Args:
            host: Redis服务器地址
            port: Redis服务器端口
            password: Redis密码（可选）
            db: Redis数据库编号
            validate_config: 是否在初始化时验证配置
        """
        # 单例模式：只在第一次初始化时设置参数
        if not hasattr(self, '_initialized'):
            # 配置验证（可选）
            if validate_config:
                if not validate_configuration():
                    raise RuntimeError("Redis配置验证失败，请检查配置后重试")

            self.host = host
            self.port = port
            self.password = password
            self.db = db

            # 连接状态管理
            self._connection_pool: Optional[redis.ConnectionPool] = None
            self._client: Optional[redis.Redis] = None
            self._connected = False
            self._last_health_check = 0
            self._connection_errors = 0
            self._max_connection_errors = self.CLIENT_CONFIG['max_connection_errors']

            # 性能统计
            self._operation_count = 0
            self._error_count = 0
            self._last_operation_time = 0
            self._start_time = time.time()

            # 初始化连接池
            self._init_connection_pool()
            self._initialized = True

    def _init_connection_pool(self) -> None:
        """初始化连接池"""
        try:
            self._connection_pool = redis.ConnectionPool(
                host=self.host,
                port=self.port,
                password=self.password,
                db=self.db,
                **self.CONNECTION_POOL_CONFIG
            )
            logging.info(f"Redis连接池初始化成功: {self.host}:{self.port}")
        except Exception as e:
            logging.error(f"Redis连接池初始化失败: {e}")
            self._connection_pool = None

    @property
    def client(self) -> redis.Redis:
        """获取Redis客户端实例（带重试机制）"""
        if self._client is None or not self._is_connection_healthy():
            self._create_client_with_retry()
        return self._client

    def _create_client_with_retry(self) -> None:
        """创建Redis客户端（带智能重试机制和指数退避）"""
        last_exception = None

        for attempt in range(self.CLIENT_CONFIG['max_retries']):
            try:
                if self._connection_pool is None:
                    self._init_connection_pool()

                if self._connection_pool is None:
                    raise redis.ConnectionError("无法初始化连接池")

                # 创建Redis客户端，使用客户端配置
                self._client = redis.Redis(
                    connection_pool=self._connection_pool,
                    retry_on_timeout=self.CLIENT_CONFIG['retry_on_timeout'],
                    socket_connect_timeout=self.CLIENT_CONFIG['connection_timeout']
                )

                # 连接测试 - 使用超时设置
                self._client.ping()
                self._connected = True
                self._connection_errors = 0
                self._last_health_check = time.time()

                if attempt > 0:
                    logging.info(f"Redis连接恢复成功 (尝试 {attempt + 1} 次)")
                else:
                    logging.info(f"Redis连接成功: {self.host}:{self.port}")

                break

            except (redis.ConnectionError, redis.TimeoutError) as e:
                last_exception = e
                self._connection_errors += 1

                # 智能指数退避：base^attempt，但不超过最大延迟
                base_delay = self.CLIENT_CONFIG['retry_delay']
                backoff_base = self.CLIENT_CONFIG['exponential_backoff_base']
                max_delay = self.CLIENT_CONFIG['max_retry_delay']

                # 计算退避延迟：base_delay * (backoff_base ^ attempt)
                wait_time = min(base_delay * (backoff_base ** attempt), max_delay)

                if attempt < self.CLIENT_CONFIG['max_retries'] - 1:
                    logging.warning(f"Redis连接失败 (尝试 {attempt + 1}/{self.CLIENT_CONFIG['max_retries']}): {e}, {wait_time:.1f}秒后重试")
                    time.sleep(wait_time)
                else:
                    self._connected = False
                    logging.error(f"Redis连接失败，已达到最大重试次数 ({self.CLIENT_CONFIG['max_retries']})，最后错误: {e}")
                    raise last_exception or redis.ConnectionError(f"连接失败，已重试 {self.CLIENT_CONFIG['max_retries']} 次")

            except Exception as e:
                # 处理其他意外错误
                last_exception = e
                self._connection_errors += 1
                logging.error(f"Redis连接出现意外错误: {e}")

                if attempt < self.CLIENT_CONFIG['max_retries'] - 1:
                    wait_time = self.CLIENT_CONFIG['retry_delay']
                    logging.warning(f"意外错误，将在 {wait_time:.1f}秒后重试")
                    time.sleep(wait_time)
                else:
                    self._connected = False
                    raise last_exception or redis.ConnectionError(f"意外连接错误，已重试 {self.CLIENT_CONFIG['max_retries']} 次")

    def _is_connection_healthy(self) -> bool:
        """检查连接是否健康"""
        # 如果从未连接过，尝试创建连接
        if self._client is None:
            try:
                # 临时创建客户端进行连接测试
                temp_client = redis.Redis(
                    connection_pool=self._connection_pool,
                    retry_on_timeout=self.CLIENT_CONFIG['retry_on_timeout']
                )
                temp_client.ping()
                # 如果连接成功，标记为已连接
                self._connected = True
                self._last_health_check = time.time()
                self._connection_errors = 0
                return True
            except redis.ConnectionError:
                self._connected = False
                return False

        # 如果已经创建了客户端，检查连接状态
        if not self._connected:
            return False

        # 定期健康检查
        current_time = time.time()
        if current_time - self._last_health_check > self.CLIENT_CONFIG['health_check_interval']:
            try:
                self._client.ping()
                self._last_health_check = current_time
                self._connection_errors = 0
                return True
            except redis.ConnectionError:
                self._connection_errors += 1
                self._connected = False
                self._last_health_check = current_time
                logging.warning(f"Redis健康检查失败，连续失败次数: {self._connection_errors}")

                # 如果连续失败次数过多，强制重连
                if self._connection_errors >= self._max_connection_errors:
                    logging.warning("Redis连续健康检查失败过多，尝试重新连接")
                    self._client = None
                    self._connection_pool = None

                return False

        return True

    def is_connected(self) -> bool:
        """检查Redis连接状态（带缓存优化）"""
        return self._is_connection_healthy()

    def get_connection_status(self) -> Dict[str, Any]:
        """获取详细的连接状态信息"""
        current_time = time.time()
        health_check_age = current_time - self._last_health_check

        status = {
            'connected': self._connected,
            'host': self.host,
            'port': self.port,
            'db': self.db,
            'has_password': self.password is not None,
            'connection_errors': self._connection_errors,
            'max_connection_errors': self._max_connection_errors,
            'last_health_check': self._last_health_check,
            'health_check_age_seconds': health_check_age,
            'health_check_interval': self.CLIENT_CONFIG['health_check_interval'],
            'needs_health_check': health_check_age > self.CLIENT_CONFIG['health_check_interval'],
            'connection_pool_exists': self._connection_pool is not None,
            'client_exists': self._client is not None,
        }

        # 如果需要健康检查，立即执行一次
        if status['needs_health_check']:
            try:
                if self._is_connection_healthy():
                    status['current_health'] = 'healthy'
                else:
                    status['current_health'] = 'unhealthy'
            except Exception as e:
                status['current_health'] = f'error: {str(e)}'
        else:
            status['current_health'] = 'cached_healthy' if self._connected else 'cached_unhealthy'

        return status

    def get_performance_stats(self) -> Dict[str, Any]:
        """获取性能统计信息"""
        return {
            'operation_count': self._operation_count,
            'error_count': self._error_count,
            'error_rate': (self._error_count / max(self._operation_count, 1)) * 100,
            'last_operation_time': self._last_operation_time,
            'average_operation_time': self._last_operation_time if self._operation_count == 1 else 0,  # 可以扩展为计算平均值
            'uptime_seconds': time.time() - getattr(self, '_start_time', time.time()),
            'connection_pool_size': getattr(self._connection_pool, '_available_connections', []) if self._connection_pool else 0,
            'client_config': self.CLIENT_CONFIG.copy(),
        }

    def reset_performance_stats(self) -> None:
        """重置性能统计信息"""
        self._operation_count = 0
        self._error_count = 0
        self._last_operation_time = 0
        logging.info("性能统计已重置")

    def log_detailed_status(self) -> None:
        """记录详细的状态信息"""
        status = self.get_connection_status()
        stats = self.get_performance_stats()

        logging.info("=" * 60)
        logging.info("Redis客户端详细状态报告")
        logging.info("=" * 60)

        logging.info("连接状态:")
        for key, value in status.items():
            logging.info(f"  {key}: {value}")

        logging.info("性能统计:")
        for key, value in stats.items():
            if key == 'client_config':
                continue
            logging.info(f"  {key}: {value}")

        logging.info("客户端配置:")
        for key, value in stats['client_config'].items():
            logging.info(f"  {key}: {value}")

        logging.info("=" * 60)

    def close(self) -> None:
        """关闭Redis连接"""
        if self._client:
            try:
                self._client.close()
            except Exception as e:
                logging.warning(f"关闭Redis连接时发生错误: {e}")

        if self._connection_pool:
            try:
                self._connection_pool.disconnect()
            except Exception as e:
                logging.warning(f"断开连接池时发生错误: {e}")

        self._client = None
        self._connection_pool = None
        self._connected = False
        logging.info("Redis连接已关闭")

    def reconnect(self) -> bool:
        """强制重新连接"""
        try:
            self.close()
            self._create_client_with_retry()
            return True
        except Exception as e:
            logging.error(f"Redis重新连接失败: {e}")
            return False

    def store_breadth_data(self, timestamp: datetime, metrics: Dict[str, int],
                          bm: int, delta: int, regime: str,
                          bm_momentum: int = 0, delta_momentum: int = 0) -> bool:
        """
        存储广度动量数据到Redis（双信号版）

        Args:
            timestamp: 数据时间戳
            metrics: 包含advancers, decliners, up5等指标的字典
            bm: BM_broad — regime稳定信号 (Pearson r≈0.94 vs net_breadth)
            delta: delta_broad — BM_broad的逐Tick变化量
            regime: 市场制度字符串
            bm_momentum: BM_momentum — 极端动能捕捉信号 (权重1:3:9)
            delta_momentum: delta_momentum — BM_momentum的逐Tick变化量

        Returns:
            bool: 成功返回True，否则返回False
        """
        start_time = time.time()
        self._operation_count += 1

        try:
            if not self.is_connected():
                logging.warning("存储数据失败：Redis连接不可用")
                self._error_count += 1
                return False

            # 验证输入参数
            if not self._validate_breadth_data(timestamp, metrics, bm, delta, regime):
                logging.error("存储数据失败：输入参数验证失败")
                self._error_count += 1
                return False

            # 转换时间戳为毫秒级（用于Redis有序集合）
            timestamp_ms = int(timestamp.timestamp() * 1000)
            record_id = f"{timestamp_ms}"

            # 转换为美东时间用于日期分组
            et_time = timestamp.astimezone(ET) if timestamp.tzinfo else timestamp.replace(tzinfo=ET)
            date_str = et_time.strftime("%Y-%m-%d")

            # 准备存储数据 (BM = BM_broad for backward compat with monitor/readers)
            data = {
                "timestamp": timestamp.isoformat(),
                "timestamp_ms": timestamp_ms,
                "advancers": metrics["advancers"],
                "decliners": metrics["decliners"],
                "up5": metrics["up5"],
                "up3_5": metrics["up3_5"],
                "up0_3": metrics["up0_3"],
                "down0_3": metrics["down0_3"],
                "down3_5": metrics["down3_5"],
                "down5": metrics["down5"],
                "BM": bm,              # BM_broad (regime signal, legacy compat)
                "delta_BM": delta,     # delta_broad
                "BM_momentum": bm_momentum,      # burst-capture signal
                "delta_momentum": delta_momentum, # burst delta
                "regime": regime,
                "net_breadth": (metrics["up5"] + metrics["up3_5"] + metrics["up0_3"] -
                               metrics["down0_3"] - metrics["down3_5"] - metrics["down5"])
            }

            # 使用管道实现原子操作（优化版）
            with self.client.pipeline(transaction=True) as pipe:
                # 添加到时间线（有序集合）
                pipe.zadd("breadth_momentum:timeline", {record_id: timestamp_ms})

                # 存储数据为哈希
                pipe.hset(f"breadth_momentum:record:{record_id}", mapping=data)

                # 更新交易日期索引
                pipe.sadd("trading_dates", date_str)

                # 添加记录到日期特定的有序集合
                pipe.zadd(f"trading_date:{date_str}", {record_id: timestamp_ms})

                # 更新日期统计（记录数量）- 原子递增
                pipe.hincrby("trading_dates:stats", date_str, 1)

                # 执行管道
                pipe.execute()

            operation_time = time.time() - start_time
            self._last_operation_time = operation_time

            logging.debug(f"存储广度数据成功: {timestamp} (耗时: {operation_time:.3f}秒)")
            return True

        except redis.ConnectionError as e:
            operation_time = time.time() - start_time
            self._error_count += 1
            self._connected = False
            logging.error(f"Redis连接错误，存储数据失败 (耗时: {operation_time:.3f}秒): {e}")
            return False
        except redis.TimeoutError as e:
            operation_time = time.time() - start_time
            self._error_count += 1
            logging.error(f"Redis操作超时，存储数据失败 (耗时: {operation_time:.3f}秒): {e}")
            return False
        except Exception as e:
            operation_time = time.time() - start_time
            self._error_count += 1
            logging.error(f"存储广度数据失败 (耗时: {operation_time:.3f}秒): {e}", exc_info=True)
            return False

    def _validate_breadth_data(self, timestamp: datetime, metrics: Dict[str, int],
                              bm: int, delta: int, regime: str) -> bool:
        """验证广度数据的输入参数"""
        try:
            # 检查时间戳
            if not isinstance(timestamp, datetime):
                logging.error(f"时间戳类型错误: {type(timestamp)}")
                return False

            # 检查必需的指标字段
            required_metrics = ["advancers", "decliners", "up5", "up3_5", "up0_3", "down0_3", "down3_5", "down5"]
            for field in required_metrics:
                if field not in metrics:
                    logging.error(f"缺少必需指标字段: {field}")
                    return False
                if not isinstance(metrics[field], int) or metrics[field] < 0:
                    logging.error(f"指标字段 {field} 必须是非负整数，当前值: {metrics[field]}")
                    return False

            # 检查BM和delta
            if not isinstance(bm, int):
                logging.error(f"BM值必须是整数，当前值: {bm} (类型: {type(bm)})")
                return False
            if not isinstance(delta, int):
                logging.error(f"Delta值必须是整数，当前值: {delta} (类型: {delta})")
                return False

            # 检查regime
            if not isinstance(regime, str) or not regime.strip():
                logging.error(f"Regime必须是非空字符串，当前值: {regime}")
                return False

            return True

        except Exception as e:
            logging.error(f"数据验证过程中发生错误: {e}")
            return False

    def store_breadth_data_batch(self, data_batch: List[Dict[str, Any]]) -> tuple[int, int]:
        """
        批量存储广度动量数据（高性能优化）

        Args:
            data_batch: 数据批次列表，每个元素包含timestamp, metrics, bm, delta, regime

        Returns:
            tuple: (成功数量, 失败数量)
        """
        if not data_batch:
            return 0, 0

        success_count = 0
        fail_count = 0

        try:
            if not self.is_connected():
                return 0, len(data_batch)

            # 分批处理，避免单次管道过大
            batch_size = 50
            for i in range(0, len(data_batch), batch_size):
                batch = data_batch[i:i + batch_size]

                with self.client.pipeline(transaction=True) as pipe:
                    for item in batch:
                        timestamp = item['timestamp']
                        metrics = item['metrics']
                        bm = item['bm']
                        delta = item['delta']
                        regime = item['regime']

                        # 转换时间戳
                        timestamp_ms = int(timestamp.timestamp() * 1000)
                        record_id = f"{timestamp_ms}"

                        # 转换为美东时间
                        et_time = timestamp.astimezone(ET) if timestamp.tzinfo else timestamp.replace(tzinfo=ET)
                        date_str = et_time.strftime("%Y-%m-%d")

                        # 准备数据
                        data = {
                            "timestamp": timestamp.isoformat(),
                            "timestamp_ms": timestamp_ms,
                            **metrics,
                            "BM": bm,
                            "delta_BM": delta,
                            "regime": regime,
                            "net_breadth": (metrics["up5"] + metrics["up3_5"] + metrics["up0_3"] -
                                           metrics["down0_3"] - metrics["down3_5"] - metrics["down5"])
                        }

                        # 批量管道操作
                        pipe.zadd("breadth_momentum:timeline", {record_id: timestamp_ms})
                        pipe.hset(f"breadth_momentum:record:{record_id}", mapping=data)
                        pipe.sadd("trading_dates", date_str)
                        pipe.zadd(f"trading_date:{date_str}", {record_id: timestamp_ms})
                        pipe.hincrby("trading_dates:stats", date_str, 1)

                    # 执行批次
                    results = pipe.execute()
                    success_count += len(batch)

            logging.info(f"批量存储完成: {success_count} 条记录成功, {fail_count} 条记录失败")
            return success_count, fail_count

        except Exception as e:
            logging.error(f"批量存储失败: {e}")
            fail_count = len(data_batch) - success_count
            return success_count, fail_count

    def get_breadth_data_range(self, start_time: datetime | None = None,
                              end_time: datetime | None = None,
                              limit: int | None = None) -> List[Dict[str, Any]]:
        """
        获取时间范围内的广度数据（优化版）

        Args:
            start_time: 时间范围开始（包含）
            end_time: 时间范围结束（包含）
            limit: 最大返回记录数

        Returns:
            按时间戳排序的数据记录列表
        """
        try:
            if not self.is_connected():
                return []

            # 转换datetime为毫秒
            min_score = "-inf" if start_time is None else start_time.timestamp() * 1000
            max_score = "+inf" if end_time is None else end_time.timestamp() * 1000

            # 从时间线获取记录ID
            if limit is not None:
                record_ids = self.client.zrangebyscore(
                    "breadth_momentum:timeline",
                    min_score,
                    max_score,
                    start=0,
                    num=limit
                )
            else:
                record_ids = self.client.zrangebyscore(
                    "breadth_momentum:timeline",
                    min_score,
                    max_score
                )

            if not record_ids:
                return []

            # 批量获取数据（管道优化）
            return self._batch_get_records(record_ids)

        except redis.ConnectionError as e:
            logging.error(f"Redis连接错误，获取数据失败: {e}")
            self._connected = False
            return []
        except Exception as e:
            logging.error(f"获取广度数据失败: {e}")
            return []

    def _batch_get_records(self, record_ids: List[str]) -> List[Dict[str, Any]]:
        """
        批量获取记录数据（高性能优化）

        Args:
            record_ids: 记录ID列表

        Returns:
            处理后的数据记录列表
        """
        if not record_ids:
            return []

        records = []

        # 分批处理，避免单次管道过大
        batch_size = 100
        for i in range(0, len(record_ids), batch_size):
            batch_ids = record_ids[i:i + batch_size]

            # 使用管道批量获取
            with self.client.pipeline() as pipe:
                for record_id in batch_ids:
                    pipe.hgetall(f"breadth_momentum:record:{record_id}")
                results = pipe.execute()

            # 处理结果
            for data in results:
                if data:
                    processed_data = self._process_record_data(data)
                    records.append(processed_data)

        return records

    def get_latest_breadth_data(self, count: int = 1) -> List[Dict[str, Any]]:
        """
        Get the most recent breadth data records

        Args:
            count: Number of records to retrieve

        Returns:
            List of most recent data records
        """
        try:
            if not self.is_connected():
                return []

            # Get latest record IDs from timeline
            record_ids = self.client.zrevrange("breadth_momentum:timeline", 0, count-1)

            if not record_ids:
                return []

            # Get data for each record
            records = []
            for record_id in record_ids:
                data = self.client.hgetall(f"breadth_momentum:record:{record_id}")
                if data:
                    processed_data = self._process_record_data(data)
                    records.append(processed_data)

            return records

        except Exception as e:
            logging.error(f"Failed to retrieve latest breadth data: {e}")
            return []

    def get_data_count(self) -> int:
        """Get total number of stored records"""
        try:
            if not self.is_connected():
                return 0
            return self.client.zcard("breadth_momentum:timeline")
        except Exception as e:
            logging.error(f"Failed to get data count: {e}")
            return 0

    def clear_all_data(self) -> bool:
        """Clear all breadth momentum data"""
        try:
            if not self.is_connected():
                return False

            # Get all record keys and trading dates
            record_ids = self.client.zrange("breadth_momentum:timeline", 0, -1)
            trading_dates = self.client.smembers("trading_dates") if self.client.exists("trading_dates") else set()

            with self.client.pipeline() as pipe:
                # Remove timeline
                pipe.delete("breadth_momentum:timeline")

                # Remove all record hashes
                for record_id in record_ids:
                    pipe.delete(f"breadth_momentum:record:{record_id}")

                # Remove trading dates index
                pipe.delete("trading_dates")
                pipe.delete("trading_dates:stats")

                # Remove all date-specific sorted sets
                for date_str in trading_dates:
                    pipe.delete(f"trading_date:{date_str}")

                pipe.execute()

            logging.info(f"Cleared {len(record_ids)} records from Redis")
            return True

        except Exception as e:
            logging.error(f"Failed to clear data: {e}")
            return False

    def _process_record_data(self, data: Dict[str, str]) -> Dict[str, Any]:
        """Convert string data from Redis back to appropriate types"""
        processed = {}
        for key, value in data.items():
            if key in ["advancers", "decliners", "up5", "up3_5", "up0_3",
                      "down0_3", "down3_5", "down5", "BM", "delta_BM", "net_breadth"]:
                processed[key] = int(value)
            elif key == "timestamp_ms":
                processed[key] = int(value)
            else:
                processed[key] = value
        return processed

    def get_trading_dates(self) -> List[str]:
        """
        Get all trading dates that have data in Redis
        Returns list of dates in YYYY-MM-DD format, sorted in ascending order
        """
        try:
            if not self.is_connected():
                return []

            dates_set = self.client.smembers("trading_dates")
            if not dates_set:
                return []

            # Sort dates in ascending order
            return sorted(list(dates_set))
        except Exception as e:
            logging.error(f"Failed to get trading dates: {e}")
            return []

    def get_trading_dates_count(self) -> int:
        """Get total number of trading dates with data"""
        try:
            if not self.is_connected():
                return 0
            return self.client.scard("trading_dates")
        except Exception as e:
            logging.error(f"Failed to get trading dates count: {e}")
            return 0

    def get_date_record_count(self, date_str: str) -> int:
        """
        Get number of records for a specific trading date

        Args:
            date_str: Date in YYYY-MM-DD format

        Returns:
            Number of records for that date
        """
        try:
            if not self.is_connected():
                return 0
            count = self.client.hget(f"trading_dates:stats", date_str)
            return int(count) if count else 0
        except Exception as e:
            logging.error(f"Failed to get date record count: {e}")
            return 0

    def get_date_data(self, date_str: str) -> List[Dict[str, Any]]:
        """
        Get all data for a specific trading date

        Args:
            date_str: Date in YYYY-MM-DD format

        Returns:
            List of records for that date
        """
        try:
            if not self.is_connected():
                return []

            # Get record IDs for this date from the sorted set
            # zrange returns the member (record_id), not the score
            record_ids = self.client.zrange(f"trading_date:{date_str}", 0, -1)

            if not record_ids:
                return []

            # 使用批量获取优化性能，避免逐个获取导致的N+1查询问题
            # 从10000次网络往返减少到约100次（batch_size=100）
            return self._batch_get_records(record_ids)
        except Exception as e:
            logging.error(f"Failed to get date data for {date_str}: {e}")
            return []

    def rebuild_trading_dates_index(self) -> bool:
        """
        Rebuild trading dates index from existing data in Redis
        Useful when starting with existing data
        """
        try:
            if not self.is_connected():
                return False

            # Clear old index
            self.client.delete("trading_dates", "trading_dates:stats")

            # Get all record IDs from timeline
            record_ids = self.client.zrange("breadth_momentum:timeline", 0, -1)

            if not record_ids:
                logging.warning("No data found in Redis timeline")
                return True

            # Rebuild index from records
            dates_stats = {}
            with self.client.pipeline() as pipe:
                for record_id in record_ids:
                    data = self.client.hgetall(f"breadth_momentum:record:{record_id}")
                    if data and "timestamp" in data:
                        timestamp_str = data["timestamp"]
                        timestamp = datetime.fromisoformat(timestamp_str)

                        # Convert to US Eastern Time for date grouping
                        et_time = timestamp.astimezone(ET) if timestamp.tzinfo else timestamp.replace(tzinfo=ET)
                        date_str = et_time.strftime("%Y-%m-%d")
                        timestamp_ms = int(timestamp.timestamp() * 1000)

                        # Add to date index
                        pipe.sadd("trading_dates", date_str)
                        pipe.zadd(f"trading_date:{date_str}", {record_id: timestamp_ms})

                        # Count records per date
                        dates_stats[date_str] = dates_stats.get(date_str, 0) + 1

                # Update stats
                for date_str, count in dates_stats.items():
                    pipe.hset("trading_dates:stats", date_str, count)

                pipe.execute()

            logging.info(f"Rebuilt trading dates index with {len(dates_stats)} dates")
            return True

        except Exception as e:
            logging.error(f"Failed to rebuild trading dates index: {e}")
            return False

    def migrate_from_csv(self, csv_path: str) -> bool:
        """
        Migrate data from CSV file to Redis

        Args:
            csv_path: Path to CSV file

        Returns:
            bool: True if migration successful
        """
        try:
            import pandas as pd

            # Read CSV file
            df = pd.read_csv(csv_path)

            # Clean column names
            df = df.loc[:, ~df.columns.str.contains("^Unnamed")]

            # Convert timestamp
            df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
            df = df.dropna(subset=["timestamp"])

            # Convert numeric columns
            num_cols = ['advancers','decliners','up5','up3_5','up0_3','down0_3','down3_5','down5','BM','delta_BM']
            for col in num_cols:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            # 只删除数值列中的NaN，不删除regime列的NaN
            df = df.dropna(subset=num_cols)

            success_count = 0
            for _, row in df.iterrows():
                metrics = {
                    "advancers": int(row["advancers"]),
                    "decliners": int(row["decliners"]),
                    "up5": int(row["up5"]),
                    "up3_5": int(row["up3_5"]),
                    "up0_3": int(row["up0_3"]),
                    "down0_3": int(row["down0_3"]),
                    "down3_5": int(row["down3_5"]),
                    "down5": int(row["down5"]),
                }

                if self.store_breadth_data(
                    row["timestamp"],
                    metrics,
                    int(row["BM"]),
                    int(row["delta_BM"]),
                    row.get("regime", "Unknown")
                ):
                    success_count += 1

            logging.info(f"Migrated {success_count} records from CSV to Redis")
            return True

        except Exception as e:
            logging.error(f"Failed to migrate from CSV: {e}")
            return False


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    try:
        # Create Redis client with configuration validation
        print("正在初始化Redis客户端...")
        client = RedisClient()

        print("\n=== Redis Breadth Momentum Client ===")
        print(f"连接状态: {'[OK] 已连接' if client.is_connected() else '[ERROR] 未连接'}")
        print(f"数据记录总数: {client.get_data_count():,}")
        print(f"交易日期数量: {client.get_trading_dates_count()}")

        # 显示连接状态详情
        status = client.get_connection_status()
        print(f"\n连接详情:")
        print(f"  主机: {status['host']}:{status['port']}")
        print(f"  数据库: {status['db']}")
        print(f"  连接错误次数: {status['connection_errors']}")
        print(f"  健康检查状态: {status['current_health']}")

        # 显示性能统计
        stats = client.get_performance_stats()
        print(f"\n性能统计:")
        print(f"  操作次数: {stats['operation_count']}")
        print(f"  错误次数: {stats['error_count']}")
        print(f"  错误率: {stats['error_rate']:.2f}%")
        print(f"  运行时间: {stats['uptime_seconds']:.1f}秒")

        # Show available trading dates
        dates = client.get_trading_dates()
        if dates:
            print(f"\n可用交易日期: {dates[:5]}{'...' if len(dates) > 5 else ''}")

            # Show latest data
            latest = client.get_latest_breadth_data(3)
            if latest:
                print("\n最新3条记录:")
                for record in latest:
                    timestamp = record['timestamp'][:19] if isinstance(record['timestamp'], str) else str(record['timestamp'])[:19]
                    print(f"  {timestamp} - BM: {record['BM']}, 制度: {record['regime']}")

        print("\n[SUCCESS] Redis客户端初始化完成，准备就绪！")

        # 可选：显示详细状态报告
        if len(dates) > 0:
            print("\n提示: 运行 client.log_detailed_status() 可查看详细状态报告")

    except Exception as e:
        print(f"[ERROR] 初始化失败: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
