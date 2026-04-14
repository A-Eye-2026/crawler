from __future__ import annotations

import json
import math
import random
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List
from urllib.parse import unquote

import requests

KST = timezone(timedelta(hours=9))

# 지점코드 -> 지역명 + 좌표 매핑 (시도/주요 시군구 단위)
AREA_LOCATIONS: Dict[str, Dict[str, Any]] = {
    "1100000000": {"name": "서울",     "lat": 37.5665, "lng": 126.9780},
    "2600000000": {"name": "부산",     "lat": 35.1796, "lng": 129.0756},
    "2700000000": {"name": "대구",     "lat": 35.8714, "lng": 128.6014},
    "2800000000": {"name": "인천",     "lat": 37.4563, "lng": 126.7052},
    "2900000000": {"name": "광주",     "lat": 35.1595, "lng": 126.8526},
    "3000000000": {"name": "대전",     "lat": 36.3504, "lng": 127.3845},
    "3100000000": {"name": "울산",     "lat": 35.5384, "lng": 129.3114},
    "3611000000": {"name": "세종",     "lat": 36.4800, "lng": 127.2890},
    "4111100000": {"name": "수원",     "lat": 37.2636, "lng": 127.0286},
    "4113500000": {"name": "성남",     "lat": 37.4196, "lng": 127.1268},
    "4115000000": {"name": "안양",     "lat": 37.3943, "lng": 126.9568},
    "4131000000": {"name": "고양",     "lat": 37.6584, "lng": 126.8320},
    "4136000000": {"name": "남양주",   "lat": 37.6360, "lng": 127.2165},
    "4146000000": {"name": "화성",     "lat": 37.1996, "lng": 126.8312},
    "4150000000": {"name": "파주",     "lat": 37.7596, "lng": 126.7798},
    "4159000000": {"name": "용인",     "lat": 37.2411, "lng": 127.1776},
    "4163000000": {"name": "평택",     "lat": 36.9921, "lng": 127.1128},
    "4211000000": {"name": "춘천",     "lat": 37.8813, "lng": 127.7298},
    "4213000000": {"name": "원주",     "lat": 37.3422, "lng": 127.9202},
    "4215000000": {"name": "강릉",     "lat": 37.7519, "lng": 128.8761},
    "4311000000": {"name": "청주",     "lat": 36.6424, "lng": 127.4890},
    "4313000000": {"name": "충주",     "lat": 36.9910, "lng": 127.9259},
    "4413000000": {"name": "천안",     "lat": 36.8151, "lng": 127.1139},
    "4418000000": {"name": "홍성",     "lat": 36.6011, "lng": 126.6608},
    "4421000000": {"name": "아산",     "lat": 36.7898, "lng": 127.0022},
    "4511000000": {"name": "전주",     "lat": 35.8242, "lng": 127.1480},
    "4513000000": {"name": "군산",     "lat": 35.9676, "lng": 126.7368},
    "4515000000": {"name": "익산",     "lat": 35.9483, "lng": 126.9577},
    "4611000000": {"name": "목포",     "lat": 34.8118, "lng": 126.3922},
    "4613000000": {"name": "여수",     "lat": 34.7604, "lng": 127.6622},
    "4615000000": {"name": "순천",     "lat": 34.9506, "lng": 127.4872},
    "4618000000": {"name": "나주",     "lat": 35.0160, "lng": 126.7107},
    "4713000000": {"name": "안동",     "lat": 36.5684, "lng": 128.7294},
    "4715000000": {"name": "구미",     "lat": 36.1195, "lng": 128.3446},
    "4717000000": {"name": "영주",     "lat": 36.8057, "lng": 128.6240},
    "4719000000": {"name": "영천",     "lat": 35.9732, "lng": 128.9381},
    "4721000000": {"name": "상주",     "lat": 36.4108, "lng": 128.1589},
    "4725000000": {"name": "경주",     "lat": 35.8562, "lng": 129.2248},
    "4728000000": {"name": "김천",     "lat": 36.1396, "lng": 128.1136},
    "4812500000": {"name": "창원",     "lat": 35.2280, "lng": 128.6811},
    "4817000000": {"name": "진주",     "lat": 35.1800, "lng": 128.1076},
    "4822000000": {"name": "통영",     "lat": 34.8544, "lng": 128.4333},
    "4824000000": {"name": "사천",     "lat": 35.0035, "lng": 128.0645},
    "4827000000": {"name": "밀양",     "lat": 35.4958, "lng": 128.7462},
    "4831000000": {"name": "거제",     "lat": 34.8803, "lng": 128.6215},
    "5011000000": {"name": "제주",     "lat": 33.4996, "lng": 126.5312},
    "5013000000": {"name": "서귀포",   "lat": 33.2541, "lng": 126.5600},
}

REQUEST_CODE_LABELS: Dict[str, str] = {
    "A41": "노인",
    "A42": "어린이",
    "A44": "농촌",
    "A45": "비닐하우스",
    "A46": "취약거주환경",
    "A47": "도로",
    "A48": "건설현장",
    "A49": "조선소",
}


class LivingWeatherAPIClient:
    """기상청 생활기상지수 조회서비스(3.0) 클라이언트."""

    def __init__(self, base_url: str, api_key: str, timeout_seconds: int = 15):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds

    def _get_latest_time(self) -> str:
        """현재 KST 기준 가장 최근 발표 시간 문자열 반환 (3시간 단위)."""
        now = datetime.now(KST)
        hour = (now.hour // 3) * 3
        return now.strftime(f"%Y%m%d{hour:02d}00")

    def fetch_and_normalize(self, request_code: str = "A42") -> List[Dict[str, Any]]:
        if not self.api_key:
            print("[!] API 키 없음 → 더미 데이터 사용")
            return self._mock_data(request_code)

        time_str = self._get_latest_time()
        decoded_key = unquote(self.api_key)

        url = f"{self.base_url}/getSenTaIdxV4"
        params = {
            "serviceKey": decoded_key,
            "areaNo": "",
            "time": time_str,
            "requestCode": request_code,
            "numOfRows": 999,
            "pageNo": 1,
            "dataType": "JSON",
        }

        try:
            print(f"[*] API 호출: time={time_str}, requestCode={request_code}")
            resp = requests.get(url, params=params, timeout=self.timeout_seconds)
            resp.raise_for_status()
            data = resp.json()

            items = (
                data.get("response", {})
                    .get("body", {})
                    .get("items", {})
                    .get("item", [])
            )
            if isinstance(items, dict):
                items = [items]

            print(f"[*] API 응답 {len(items)}건")
            normalized = self._normalize(items)

            if not normalized and items:
                print("[!] 좌표 매핑 지역 없음 → 더미 데이터 사용")
                return self._mock_data(request_code)

            return normalized
        except Exception as e:
            print(f"[!] API 호출 실패: {e} → 더미 데이터 사용")
            return self._mock_data(request_code)

    def _normalize(self, items: List[Dict]) -> List[Dict[str, Any]]:
        synced_at = datetime.now(timezone.utc).isoformat()
        result = []

        for item in items:
            area_no = str(item.get("areaNo", ""))
            if area_no not in AREA_LOCATIONS:
                continue

            loc = AREA_LOCATIONS[area_no]

            # h1~h78 전체 시간대 예보값 추출
            forecast: Dict[str, float] = {}
            for h in range(1, 79):
                raw = item.get(f"h{h}")
                if raw is not None:
                    try:
                        forecast[f"h{h}"] = float(raw)
                    except (ValueError, TypeError):
                        pass

            result.append({
                "area_no": area_no,
                "area_name": loc["name"],
                "lat": loc["lat"],
                "lng": loc["lng"],
                "request_code": str(item.get("code", "")),
                "index_value": forecast.get("h1"),
                "forecast_json": json.dumps(forecast),
                "published_at": str(item.get("date", "")),
                "synced_at": synced_at,
            })

        return result

    def _mock_data(self, request_code: str) -> List[Dict[str, Any]]:
        """API 키가 없을 때 사용할 더미 데이터 (일주기 온도 변화 패턴 반영)."""
        synced_at = datetime.now(timezone.utc).isoformat()
        published_at = self._get_latest_time()
        result = []

        for area_no, loc in AREA_LOCATIONS.items():
            base_temp = round(random.uniform(28.0, 42.0), 1)
            forecast: Dict[str, float] = {}
            for h in range(1, 79):
                # 14시 최고, 04시 최저의 일주기 패턴
                hour_of_day = h % 24
                variation = 4 * math.sin((hour_of_day - 4) * math.pi / 12)
                forecast[f"h{h}"] = round(
                    base_temp + variation + random.uniform(-0.5, 0.5), 1
                )

            result.append({
                "area_no": area_no,
                "area_name": loc["name"],
                "lat": loc["lat"],
                "lng": loc["lng"],
                "request_code": request_code,
                "index_value": forecast.get("h1"),
                "forecast_json": json.dumps(forecast),
                "published_at": published_at,
                "synced_at": synced_at,
            })

        return result
