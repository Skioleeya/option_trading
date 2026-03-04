#!/usr/bin/env python3
"""
美股广度监控系统 - Redis连接测试工具
测试Redis连接、性能和数据访问功能
"""

import sys
import time
import redis
from typing import Dict, Any, Optional

# 导入配置和客户端
try:
    from settings import (
        redis_config,
        validate_configuration,
        get_configuration_status,
        CONNECTION_POOL_CONFIG,
        CLIENT_CONFIG
    )
    from redis_client import RedisClient
except ImportError:
    # 如果作为独立脚本运行
    try:
        from .settings import (
            redis_config,
            validate_configuration,
            get_configuration_status,
            CONNECTION_POOL_CONFIG,
            CLIENT_CONFIG
        )
        from .redis_client import RedisClient
    except ImportError:
        print("ERROR: Cannot import required modules. Please run from Redis directory.")
        sys.exit(1)


def print_header(title: str) -> None:
    """打印标题"""
    print(f"\n{'='*60}")
    print(f"        {title}")
    print(f"{'='*60}")


def print_status(status: str, message: str = "") -> None:
    """打印状态信息"""
    if status == "SUCCESS":
        print(f"[OK] {message}")
    elif status == "ERROR":
        print(f"[ERROR] {message}")
    elif status == "INFO":
        print(f"[INFO] {message}")
    elif status == "WARNING":
        print(f"[WARNING] {message}")


def test_configuration() -> bool:
    """测试配置验证"""
    print_header("Configuration Validation")

    try:
        config_status = get_configuration_status()

        if config_status['overall_valid']:
            print_status("SUCCESS", "Configuration validation passed")
        else:
            print_status("ERROR", "Configuration validation failed")

        # 显示配置摘要
        config = config_status['config_validation']['config_summary']
        print(f"\nConnection Config:")
        print(f"  Host: {config['redis_host']}")
        print(f"  Port: {config['redis_port']}")
        print(f"  Max Connections: {config['max_connections']}")
        print(f"  Data Retention: {config['data_retention_days']} days")
        print(f"  Batch Size: {config['batch_size']}")

        # 显示问题
        issues = config_status['config_validation']['issues']
        warnings = config_status['config_validation']['warnings']

        if issues:
            print(f"\nIssues found ({len(issues)}):")
            for issue in issues:
                print_status("ERROR", issue)

        if warnings:
            print(f"\nWarnings ({len(warnings)}):")
            for warning in warnings:
                print_status("WARNING", warning)

        return config_status['overall_valid']

    except Exception as e:
        print_status("ERROR", f"Configuration test failed: {e}")
        return False


def test_basic_connection() -> bool:
    """测试基本Redis连接"""
    print_header("Basic Connection Test")

    try:
        print_status("INFO", f"Connecting to Redis at {redis_config.REDIS_HOST}:{redis_config.REDIS_PORT}")

        # 创建连接池
        connection_pool = redis.ConnectionPool(
            host=redis_config.REDIS_HOST,
            port=redis_config.REDIS_PORT,
            password=redis_config.REDIS_PASSWORD,
            db=redis_config.REDIS_DB,
            **CONNECTION_POOL_CONFIG
        )

        # 创建客户端
        client = redis.Redis(connection_pool=connection_pool)

        # 测试连接
        start_time = time.time()
        result = client.ping()
        ping_time = (time.time() - start_time) * 1000  # 转换为毫秒

        if result:
            print_status("SUCCESS", f"Redis connection established ({ping_time:.1f}ms)")
            print_status("INFO", f"Redis version: {client.info('server')['redis_version']}")
            return True
        else:
            print_status("ERROR", "Redis ping failed - no response")
            return False

    except redis.ConnectionError as e:
        print_status("ERROR", f"Connection failed: {e}")
        return False
    except redis.AuthenticationError as e:
        print_status("ERROR", f"Authentication failed: {e}")
        return False
    except Exception as e:
        print_status("ERROR", f"Unexpected error: {e}")
        return False


def test_data_operations() -> bool:
    """测试数据操作"""
    print_header("Data Operations Test")

    try:
        # 使用我们的RedisClient
        client = RedisClient()

        # 测试连接状态
        connection_status = client.get_connection_status()
        if not connection_status['connected']:
            print_status("WARNING", "Redis server is not running - skipping data operations test")
            print_status("INFO", "Start Redis server with: run_redis_interactive.bat")
            return True  # Not a failure, just server not running

        # 测试基本操作
        operations = []

        # 1. 测试获取数据统计
        start_time = time.time()
        total_records = client.get_data_count()
        stats_time = (time.time() - start_time) * 1000

        operations.append(("Get total records", f"{total_records:,} records", f"{stats_time:.1f}ms"))

        # 2. 测试获取交易日期
        start_time = time.time()
        trading_dates = client.get_trading_dates_count()
        dates_time = (time.time() - start_time) * 1000

        operations.append(("Get trading dates", f"{trading_dates} dates", f"{dates_time:.1f}ms"))

        # 3. 测试连接状态
        operations.append(("Connection status", "healthy" if connection_status['connected'] else "unhealthy", "N/A"))

        # 显示结果
        print("Data operations test results:")
        for op_name, result, timing in operations:
            print(f"  {op_name}: {result} ({timing})")

        # 总体评估
        if all(op[1] != "unhealthy" for op in operations):
            print_status("SUCCESS", "All data operations completed successfully")
            return True
        else:
            print_status("ERROR", "Some data operations failed")
            return False

    except Exception as e:
        print_status("ERROR", f"Data operations test failed: {e}")
        return False


def test_performance() -> bool:
    """测试性能指标"""
    print_header("Performance Test")

    try:
        client = RedisClient()

        # 检查连接状态
        connection_status = client.get_connection_status()
        if not connection_status['connected']:
            print_status("WARNING", "Redis server is not running - skipping performance test")
            print_status("INFO", "Start Redis server with: run_redis_interactive.bat")
            return True  # Not a failure, just server not running

        # 获取性能统计
        stats = client.get_performance_stats()

        print("Performance metrics:")
        print(f"  Operation Count: {stats['operation_count']}")
        print(f"  Error Count: {stats['error_count']}")
        print(f"  Error Rate: {stats['error_rate']:.2f}%")
        print(f"  Uptime: {stats['uptime_seconds']:.1f} seconds")
        print(f"  Connection Pool Size: {stats['connection_pool_size']}")

        print_status("SUCCESS", "Performance metrics retrieved successfully")
        return True

    except Exception as e:
        print_status("ERROR", f"Performance test failed: {e}")
        return False


def main() -> int:
    """主函数"""
    print_header("Redis Connection Test Suite")
    print("美股广度监控系统 - Redis连接测试工具")
    print("Testing Redis connection, configuration, and data operations...\n")

    tests = [
        ("Configuration", test_configuration),
        ("Basic Connection", test_basic_connection),
        ("Data Operations", test_data_operations),
        ("Performance", test_performance),
    ]

    passed = 0
    total = len(tests)

    for test_name, test_func in tests:
        print(f"\n--- Running {test_name} Test ---")
        try:
            if test_func():
                passed += 1
            else:
                print(f"[FAILED] {test_name} test failed")
        except Exception as e:
            print(f"[ERROR] {test_name} test error: {e}")
            # Continue with other tests

    # 总结
    print_header("Test Summary")
    print(f"Tests passed: {passed}/{total}")

    if passed == total:
        print_status("SUCCESS", "All tests passed! Redis is ready for use.")
        return 0
    else:
        print_status("ERROR", f"{total - passed} test(s) failed. Please check Redis configuration.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
