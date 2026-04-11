from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List, Optional

import requests


class RestAreaAPIClient:
    """한국도로공사/공공데이터 API 연동 담당 클래스.

    실제 운영 전에는 응답 스펙에 맞춘 필드 매핑을 별도 어댑터로 분리하는 것이 좋다.
    현재는 MVP이므로 다음 2가지 역할만 담당한다.
    1) 외부 API 호출
    2) 내부 표준 스키마로 정규화
    """

    def __init__(self, base_url: str, api_key: str, timeout_seconds: int = 10):
        self.base_url = base_url
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds

    def fetch_raw_data(self) -> Dict:
        """외부 API 원본 데이터를 가져온다.

        현재 API 키가 없을 때도 로컬 개발이 가능하도록 예시 데이터를 fallback으로 제공한다.
        """
        if not self.api_key:
            return self._mock_response()

        params = {
            "key": self.api_key,
            "type": "json",
            "numOfRows": 300,
            "pageNo": 1,
        }

        try:
            response = requests.get(
                self.base_url,
                params=params,
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as exc:
            # 외부 API 장애 시 전체 서비스가 죽지 않도록 상위 계층에서 fallback 가능하게 예외를 그대로 전달한다.
            raise RuntimeError(f"휴게소 API 호출 실패: {exc}") from exc

    def normalize_rest_areas(self, payload: Dict) -> List[Dict]:
        """외부 응답을 내부 표준 포맷으로 변환한다.

        실제 한국도로공사 API 응답 필드가 확정되면 아래 mapping만 수정하면 된다.
        """
        synced_at = datetime.now(timezone.utc).isoformat()

        items = payload.get("items") or payload.get("list") or []
        normalized: List[Dict] = []

        for item in items:
            total_spaces = int(item.get("total_parking_spaces", 0) or 0)
            occupied_spaces = int(item.get("occupied_parking_spaces", 0) or 0)
            available_spaces = item.get("available_parking_spaces")
            if available_spaces is None:
                available_spaces = max(total_spaces - occupied_spaces, 0)

            normalized.append(
                {
                    "external_id": str(item.get("external_id") or item.get("service_id") or item.get("id") or ""),
                    "name": item.get("name", "이름 없음"),
                    "route_name": item.get("route_name", "노선 정보 없음"),
                    "lat": float(item.get("lat", 37.5665)),
                    "lng": float(item.get("lng", 126.9780)),
                    "total_parking_spaces": total_spaces,
                    "occupied_parking_spaces": occupied_spaces,
                    "available_parking_spaces": int(available_spaces),
                    "ev_charger_count": int(item.get("ev_charger_count", 0) or 0),
                    "restaurant_congestion_level": item.get("restaurant_congestion_level"),
                    "source_name": item.get("source_name", "ex_api"),
                    "last_synced_at": item.get("last_synced_at", synced_at),
                }
            )

        return normalized

    def fetch_and_normalize(self) -> List[Dict]:
        payload = self.fetch_raw_data()
        return self.normalize_rest_areas(payload)

    @staticmethod
    def _mock_response() -> Dict:
        """API 키가 없을 때도 화면/DB/엔드포인트를 바로 확인할 수 있도록 더미 데이터를 제공한다."""
        now = datetime.now(timezone.utc).isoformat()
        return {
            "items": [
                {
                    "external_id": "ra-001",
                    "name": "덕평휴게소",
                    "route_name": "영동고속도로",
                    "lat": 37.2661,
                    "lng": 127.3758,
                    "total_parking_spaces": 320,
                    "occupied_parking_spaces": 240,
                    "available_parking_spaces": 80,
                    "ev_charger_count": 6,
                    "restaurant_congestion_level": "MEDIUM",
                    "source_name": "mock",
                    "last_synced_at": now,
                },
                {
                    "external_id": "ra-002",
                    "name": "만남의광장휴게소",
                    "route_name": "경부고속도로",
                    "lat": 37.4625,
                    "lng": 127.0407,
                    "total_parking_spaces": 180,
                    "occupied_parking_spaces": 165,
                    "available_parking_spaces": 15,
                    "ev_charger_count": 4,
                    "restaurant_congestion_level": "HIGH",
                    "source_name": "mock",
                    "last_synced_at": now,
                },
                {
                    "external_id": "ra-003",
                    "name": "천안삼거리휴게소",
                    "route_name": "경부고속도로",
                    "lat": 36.7865,
                    "lng": 127.1730,
                    "total_parking_spaces": 220,
                    "occupied_parking_spaces": 90,
                    "available_parking_spaces": 130,
                    "ev_charger_count": 8,
                    "restaurant_congestion_level": "LOW",
                    "source_name": "mock",
                    "last_synced_at": now,
                },
            ]
        }
