use crate::arrow_ipc::{ArrowIpcReadCursor, ArrowIpcSegment};
use std::time::{SystemTime, UNIX_EPOCH};

fn unique_name() -> String {
    format!(
        "arrow_ipc_test_{}",
        SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .expect("clock")
            .as_nanos()
    )
}

#[test]
fn queued_transport_preserves_batch_order() {
    let name = unique_name();
    let mut writer = ArrowIpcSegment::create_or_open(&name, 256 * 1024).expect("writer");
    let reader = ArrowIpcSegment::open_readonly(&name, 256 * 1024).expect("reader");
    let mut cursor = ArrowIpcReadCursor::default();
    writer.write_message(b"first").expect("write1");
    writer.write_message(b"second").expect("write2");
    writer.write_message(b"third").expect("write3");
    assert_eq!(reader.read_next_message(&mut cursor).expect("read1"), Some(b"first".to_vec()));
    assert_eq!(reader.read_next_message(&mut cursor).expect("read2"), Some(b"second".to_vec()));
    assert_eq!(reader.read_next_message(&mut cursor).expect("read3"), Some(b"third".to_vec()));
}

#[test]
fn queued_transport_keeps_batches_for_independent_readers() {
    let name = unique_name();
    let mut writer = ArrowIpcSegment::create_or_open(&name, 256 * 1024).expect("writer");
    let reader = ArrowIpcSegment::open_readonly(&name, 256 * 1024).expect("reader");
    let mut first = ArrowIpcReadCursor::default();
    let mut second = ArrowIpcReadCursor::default();
    writer.write_message(b"alpha").expect("write1");
    writer.write_message(b"beta").expect("write2");
    assert_eq!(reader.read_next_message(&mut first).expect("first1"), Some(b"alpha".to_vec()));
    assert_eq!(reader.read_next_message(&mut second).expect("second1"), Some(b"alpha".to_vec()));
    assert_eq!(reader.read_next_message(&mut first).expect("first2"), Some(b"beta".to_vec()));
    assert_eq!(reader.read_next_message(&mut second).expect("second2"), Some(b"beta".to_vec()));
}
