import json
import logging
import random
from typing import Dict, List, TYPE_CHECKING

import requests
from websocket import create_connection

if TYPE_CHECKING:
    from config.config import Config

SEGMENT_KEYS: List[str] = [
    "up0",
    "up0_3",
    "up3_5",
    "up5",
    "down0_3",
    "down3_5",
    "down5",
]


class LongbridgeClient:
    def __init__(self, config: "Config") -> None:
        """
        初始化 Longbridge 客户端
        
        Args:
            config: 配置对象，包含 API 端点和认证信息
        """
        self.config = config
        self.session = requests.Session()
        headers = {
            "User-Agent": config.user_agent,
            "Referer": config.referrer,
            "Origin": config.origin,
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": config.accept_language,
        }
        if config.cookie:
            headers["Cookie"] = config.cookie
        if config.authorization:
            headers["Authorization"] = config.authorization
        elif config.token:
            headers["Authorization"] = f"Bearer {config.token}"

        if config.account_channel:
            headers["account-channel"] = config.account_channel
        if config.x_api_key:
            headers["x-api-key"] = config.x_api_key
        if config.x_api_signature:
            headers["x-api-signature"] = config.x_api_signature
        if config.x_app_id:
            headers["x-app-id"] = config.x_app_id
        if config.x_application_build:
            headers["x-application-build"] = config.x_application_build
        if config.x_application_version:
            headers["x-application-version"] = config.x_application_version
        if config.x_bundle_id:
            headers["x-bundle-id"] = config.x_bundle_id
        if config.x_device_id:
            headers["x-device-id"] = config.x_device_id
        if config.x_engine_version:
            headers["x-engine-version"] = config.x_engine_version
        if config.x_platform:
            headers["x-platform"] = config.x_platform
        if config.x_request_id:
            headers["x-request-id"] = config.x_request_id
        if config.x_target_aaid:
            headers["x-target-aaid"] = config.x_target_aaid
        if config.x_timestamp:
            headers["x-timestamp"] = config.x_timestamp
        self.session.headers.update(headers)

    def get_latest(self) -> Dict[str, int]:
        if self.config.demo_mode:
            return self._demo_payload()

        if self.config.data_url:
            return self._fetch_http_snapshot()

        if self.config.ws_url:
            return self._fetch_ws_snapshot()

        raise ValueError("No data source configured (DATA_URL, WS_URL, or DEMO_MODE)")

    def _fetch_http_snapshot(self) -> Dict[str, int]:
        logging.debug("Requesting breadth data via HTTP: %s", self.config.data_url)
        resp = self.session.get(self.config.data_url, timeout=10)
        resp.raise_for_status()
        payload = resp.json()
        return self._normalize_payload(payload)

    def _fetch_ws_snapshot(self) -> Dict[str, int]:
        logging.debug("Requesting breadth data via WebSocket: %s", self.config.ws_url)
        headers = []
        if self.config.cookie:
            headers.append(f"Cookie: {self.config.cookie}")
        if self.config.token:
            headers.append(f"Authorization: Bearer {self.config.token}")

        ws = create_connection(self.config.ws_url, header=headers or None, timeout=10)
        try:
            message = ws.recv()
            payload = json.loads(message)
            return self._normalize_payload(payload)
        finally:
            ws.close()

    def _normalize_payload(self, payload: Dict) -> Dict[str, int]:
        """
        Normalize upstream JSON into the expected bucket keys.

        Supports two layouts:
        1) Direct buckets: up3/up1_3/up0_1/down0_1/down1_3/down3 (+ optional advancers/decliners/flat)
        2) Longbridge counter layout (fields like rise_less_than_three, fall_more_than_seven, flatline)
           mapped approximately into the BM buckets.
        """
        if not isinstance(payload, dict):
            raise ValueError("Breadth payload must be a JSON object")

        if "rise_less_than_three" in payload or (
            isinstance(payload.get("data"), dict)
            and "rise_less_than_three" in payload["data"]
        ):
            return self._normalize_counter_payload(payload)

        metrics: Dict[str, int] = {}
        for key in SEGMENT_KEYS:
            if key not in payload:
                raise KeyError(f"Missing field: {key}")
            metrics[key] = int(payload[key])

        advancers = payload.get("advancers")
        if advancers is None:
            advancers = sum(metrics[k] for k in ("up0_3", "up3_5", "up5"))
        decliners = payload.get("decliners")
        if decliners is None:
            decliners = sum(metrics[k] for k in ("down0_3", "down3_5", "down5"))

        metrics["advancers"] = int(advancers)
        metrics["decliners"] = int(decliners)
        metrics["flat"] = int(payload.get("flat", 0))
        return metrics

    def _normalize_counter_payload(self, payload: Dict) -> Dict[str, int]:
        """
        Map Longbridge statics?counter_id payload into BM buckets.

        Mapping (approximate due to coarse buckets):
        - up5   : rise_more_than_seven + rise_five_to_seven (>=5%)
        - up3_5 : rise_three_to_five (3%~5%)
        - up0_3 : rise_less_than_three (0%~3%)
        - down5   : fall_more_than_seven + fall_five_to_seven (<=-5%)
        - down3_5 : fall_three_to_five (-5%~-3%)
        - down0_3 : fall_less_than_three (0%~-3%)
        - flat / halted are ignored (set to 0) per requirements
        """
        data = payload.get("data", payload)

        def val(name: str) -> int:
            if name not in data:
                raise KeyError(f"Missing field: {name}")
            return int(data[name])

        up5 = val("rise_more_than_seven") + val("rise_five_to_seven")
        up3_5 = val("rise_three_to_five")
        up0_3 = val("rise_less_than_three")
        up0 = 0
        down5 = val("fall_more_than_seven") + val("fall_five_to_seven")
        down3_5 = val("fall_three_to_five")
        down0_3 = val("fall_less_than_three")
        down0 = 0
        flat = 0  # explicitly ignore flatline / halted counts per requirements

        advancers = up0_3 + up3_5 + up5
        decliners = down0_3 + down3_5 + down5

        return {
            "up0": up0,
            "up0_3": up0_3,
            "up3_5": up3_5,
            "up5": up5,
            "down0_3": down0_3,
            "down3_5": down3_5,
            "down5": down5,
            "down0": down0,
            "advancers": advancers,
            "decliners": decliners,
            "flat": flat,
        }

    def _demo_payload(self) -> Dict[str, int]:
        # Generate a reproducible but varied demo snapshot for quick testing.
        base = random.randint(1500, 2500)
        up5 = random.randint(20, 120)
        up3_5 = random.randint(120, 300)
        up0_3 = random.randint(300, 700)
        up0 = random.randint(0, 50)
        down5 = random.randint(20, 120)
        down3_5 = random.randint(120, 300)
        down0_3 = random.randint(300, 700)
        down0 = random.randint(0, 50)
        used = up5 + up3_5 + up0_3 + down0_3 + down3_5 + down5 + up0 + down0
        flat = max(base - used, 0)
        return {
            "advancers": up0_3 + up3_5 + up5,
            "decliners": down0_3 + down3_5 + down5,
            "flat": flat,
            "up0": up0,
            "up0_3": up0_3,
            "up3_5": up3_5,
            "up5": up5,
            "down0_3": down0_3,
            "down3_5": down3_5,
            "down5": down5,
            "down0": down0,
        }

