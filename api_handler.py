from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

import requests


class RestAreaAPIClient:
    """한국도로공사(EX) 전용 지능형 API 핸들러 (위치 + 주차정보 병합)."""

    def __init__(self, base_url: str, api_key: str, timeout_seconds: int = 15):
        # base_url: https://data.ex.co.kr/openapi
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds

    def _call_api(self, path: str) -> List[Dict[str, Any]]:
        """특정 경로의 API를 호출하여 데이터 리스트를 반환한다."""
        from urllib.parse import unquote
        decoded_key = unquote(self.api_key)
        
        target_url = f"{self.base_url}/{path}"
        params = {
            "key": decoded_key,
            "type": "json",
            "numOfRows": 999,
            "pageNo": 1
        }

        try:
            print(f"[*] API 호출 중: {target_url}")
            response = requests.get(target_url, params=params, timeout=self.timeout_seconds)
            response.raise_for_status()
            data = response.json()
            items = data.get("list", [])
            print(f"[*] 성공: {len(items)}건의 데이터를 가져왔습니다.")
            return items
        except Exception as e:
            print(f"[!] API 호출 실패 ({path}): {e}")
            return []

    def fetch_and_normalize(self) -> List[Dict[str, Any]]:
        """두 가지 API를 호출하여 위치와 주차 정보를 병합한 데이터를 생성한다."""
        synced_at = datetime.now(timezone.utc).isoformat()
        
        # 1) 위치 정보 가져오기 (xValue, yValue)
        loc_items = self._call_api("locationinfo/locationinfoRest")
        
        # 2) 상세 주차 정보 가져오기 (cocrPrkgTrcn 등)
        park_items = self._call_api("restinfo/hiwaySvarInfoList")

        # 3) 데이터 병합 (이름 + 노선명을 키로 사용)
        # 키: "가남(창원)졸음쉼터 (상행)|영동선"
        merged_data: Dict[str, Dict[str, Any]] = {}

        # 먼저 위치 정보로 기본 틀 생성
        for loc in loc_items:
            name = loc.get("unitName", "이름 없음")
            route = loc.get("routeName", "노선 없음")
            key = f"{name}|{route}"
            
            lat = float(loc.get("yValue") or 0)
            lng = float(loc.get("xValue") or 0)
            
            if lat == 0 or lng == 0: continue

            merged_data[key] = {
                "external_id": str(loc.get("unitCode") or name),
                "name": name,
                "route_name": route,
                "lat": lat,
                "lng": lng,
                "total_parking_spaces": 0,
                "occupied_parking_spaces": 0,
                "available_parking_spaces": 0,
                "ev_charger_count": 0,
                "restaurant_congestion_level": None,
                "source_name": "EX_API_MERGED",
                "last_synced_at": synced_at,
            }

        # 주차 정보를 병합 (이름 매칭)
        for park in park_items:
            name = park.get("svarNm", "이름 없음")
            # 방향 정보 보정
            direction = park.get("gudClssNm")
            if direction and direction not in name:
                name = f"{name} ({direction})"
            
            route = park.get("routeNm", "노선 없음")
            key = f"{name}|{route}"

            # 주차장 데이터 합산
            total = (
                int(float(park.get("cocrPrkgTrcn") or 0)) +
                int(float(park.get("fscarPrkgTrcn") or 0)) +
                int(float(park.get("dspnPrkgTrcn") or 0))
            )

            if key in merged_data:
                merged_data[key]["total_parking_spaces"] = total
                merged_data[key]["available_parking_spaces"] = total
                merged_data[key]["external_id"] = str(park.get("svarCd") or merged_data[key]["external_id"])
            else:
                # 좌표가 없더라도 주차 정보만 있는 데이터가 있다면 서울 시청 대신 위치 정보가 있는 것 위주로 표시
                # (여기에 위치 정보가 없는 데이터는 건너뜁니다)
                pass

        return list(merged_data.values())

    @staticmethod
    def _mock_response() -> Dict[str, Any]:
        return {"list": []}
