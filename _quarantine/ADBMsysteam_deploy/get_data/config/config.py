"""
美股广度数据生成者系统 - 配置管理 (兼容层)
保持向后兼容，同时迁移到零硬编码的settings系统
"""

from dataclasses import dataclass
from typing import Optional
from .settings import (
    get_longbridge_config, get_system_config,
    get_google_sheets_config, TZ_NY
)


@dataclass
class Config:
    """
    兼容性配置类
    保持原有接口，同时使用新的settings系统
    """
    # Longbridge API配置
    data_url: str
    ws_url: str
    cookie: Optional[str]
    token: Optional[str]
    authorization: Optional[str]
    referrer: str
    origin: str
    accept_language: str
    account_channel: Optional[str]
    x_api_key: Optional[str]
    x_api_signature: Optional[str]
    x_app_id: Optional[str]
    x_application_build: Optional[str]
    x_application_version: Optional[str]
    x_bundle_id: Optional[str]
    x_device_id: Optional[str]
    x_engine_version: Optional[str]
    x_platform: Optional[str]
    x_request_id: Optional[str]
    x_target_aaid: Optional[str]
    x_timestamp: Optional[str]
    user_agent: str

    # 系统配置
    refresh_interval: int
    csv_path: Optional[str]
    demo_mode: bool

    # Google Sheets配置
    gs_credentials_path: Optional[str]
    gs_sheet_id: Optional[str]
    gs_range: str
    gs_overwrite: bool

    # Redis配置
    redis_host: str
    redis_port: int
    redis_password: Optional[str]
    redis_db: int
    use_redis: bool


def load_config() -> Config:
    """
    加载配置 (零硬编码实现)

    从settings系统加载所有配置，实现完全的外部化管理

    Returns:
        Config: 配置对象
    """
    # 获取各个配置模块
    lb_config = get_longbridge_config()
    sys_config = get_system_config()
    gs_config = get_google_sheets_config()

    return Config(
        # Longbridge API配置
        data_url=lb_config.DATA_URL,
        ws_url=lb_config.WS_URL,
        cookie=lb_config.LB_COOKIE,
        token=lb_config.LB_TOKEN,
        authorization=lb_config.AUTHORIZATION,
        referrer=lb_config.REFERRER,
        origin=lb_config.ORIGIN,
        accept_language=lb_config.ACCEPT_LANGUAGE,
        account_channel=lb_config.ACCOUNT_CHANNEL,
        x_api_key=lb_config.X_API_KEY,
        x_api_signature=lb_config.X_API_SIGNATURE,
        x_app_id=lb_config.X_APP_ID,
        x_application_build=lb_config.X_APPLICATION_BUILD,
        x_application_version=lb_config.X_APPLICATION_VERSION,
        x_bundle_id=lb_config.X_BUNDLE_ID,
        x_device_id=lb_config.X_DEVICE_ID,
        x_engine_version=lb_config.X_ENGINE_VERSION,
        x_platform=lb_config.X_PLATFORM,
        x_request_id=lb_config.X_REQUEST_ID,
        x_target_aaid=lb_config.X_TARGET_AAID,
        x_timestamp=lb_config.X_TIMESTAMP,
        user_agent=lb_config.USER_AGENT,

        # 系统配置
        refresh_interval=sys_config.REFRESH_INTERVAL,
        csv_path=sys_config.CSV_PATH,
        demo_mode=sys_config.DEMO_MODE,

        # Google Sheets配置
        gs_credentials_path=gs_config.GS_CREDENTIALS_PATH,
        gs_sheet_id=gs_config.GS_SHEET_ID,
        gs_range=gs_config.GS_RANGE,
        gs_overwrite=gs_config.GS_OVERWRITE,

        # Redis配置
        redis_host=sys_config.REDIS_HOST,
        redis_port=sys_config.REDIS_PORT,
        redis_password=sys_config.REDIS_PASSWORD,
        redis_db=sys_config.REDIS_DB,
        use_redis=sys_config.USE_REDIS,
    )
