from __future__ import annotations

import json
import math
import random
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
from urllib.parse import unquote

import requests

KST = timezone(timedelta(hours=9))

# ── 예보 시간 배열 ──────────────────────────────────────────────────────────
SENSATION_HOURS: List[int] = list(range(1, 79))       # h1 ~ h78  (1시간 단위)
UV_HOURS:        List[int] = list(range(0, 76, 3))    # h0 ~ h75  (3시간 단위)
AIR_HOURS:       List[int] = list(range(3, 79, 3))    # h3 ~ h78  (3시간 단위)

# ── 지점코드 좌표 매핑 ───────────────────────────────────────────────────────
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

# ── 요청 코드 레이블 ─────────────────────────────────────────────────────────
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

EXTRA_INDEX_LABELS: Dict[str, str] = {
    "UV":  "자외선지수",
    "AIR": "대기정체지수",
}

ALL_REQUEST_CODES: Dict[str, str] = {**REQUEST_CODE_LABELS, **EXTRA_INDEX_LABELS}


class LivingWeatherAPIClient:
    """기상청 생활기상지수 조회서비스(3.0) 통합 클라이언트.

    getSenTaIdxV4  - 대상환경별 체감온도 (5~9월)
    getUVIdxV4     - 자외선지수
    getAirDiffusionIdxV4 - 대기정체지수
    """

    def __init__(self, base_url: str, api_key: str, timeout_seconds: int = 15):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds

    # ── 공개 API ──────────────────────────────────────────────────────────────

    def fetch_and_normalize(self, request_code: str = "A42") -> List[Dict[str, Any]]:
        if not self.api_key:
            print(f"[!] API 키 없음 → {request_code} 더미 데이터 사용")
            return self._mock_data(request_code)

        if request_code == "UV":
            return self._call("getUVIdxV4", None, UV_HOURS, "UV")
        elif request_code == "AIR":
            return self._call("getAirDiffusionIdxV4", None, AIR_HOURS, "AIR")
        else:
            return self._call("getSenTaIdxV4", request_code, SENSATION_HOURS, request_code)

    # ── 내부 공통 호출 ────────────────────────────────────────────────────────

    def _call(
        self,
        endpoint: str,
        request_code: Optional[str],
        hours: List[int],
        store_code: str,
    ) -> List[Dict[str, Any]]:
        # UV/AIR는 하루 1회 00:00 발표, 체감온도는 3시간 주기
        if store_code in ("UV", "AIR"):
            time_str = self._get_time_daily()
        else:
            time_str = self._get_time_3hourly()

        url = f"{self.base_url}/{endpoint}"
        params: Dict[str, Any] = {
            "serviceKey": unquote(self.api_key),
            "areaNo": "",
            "time": time_str,
            "numOfRows": 9999,
            "pageNo": 1,
            "dataType": "JSON",
        }
        if request_code:
            params["requestCode"] = request_code

        try:
            print(f"[*] API 호출: {endpoint}, time={time_str}" +
                  (f", requestCode={request_code}" if request_code else ""))
            resp = requests.get(url, params=params, timeout=self.timeout_seconds)
            resp.raise_for_status()
            raw_items = self._extract_items(resp.json())
            print(f"[*] 응답: {len(raw_items)}건")
            if not raw_items:
                print(f"[!] 데이터 0건 (시즌 외 또는 발표 전) → {store_code} 더미 데이터 사용")
                return self._mock_data(store_code)
            normalized = self._normalize(raw_items, store_code, hours)
            if not normalized:
                print(f"[!] 좌표 매핑 없음 → {store_code} 더미 데이터 사용")
                return self._mock_data(store_code)
            return normalized
        except Exception as e:
            print(f"[!] {endpoint} 실패: {e} → 더미 데이터 사용")
            return self._mock_data(store_code)

    def _extract_items(self, data: dict) -> List[Dict]:
        items = (
            data.get("response", {})
                .get("body", {})
                .get("items", {})
                .get("item", [])
        )
        return [items] if isinstance(items, dict) else items

    def _normalize(
        self,
        items: List[Dict],
        store_code: str,
        hours: List[int],
    ) -> List[Dict[str, Any]]:
        synced_at = datetime.now(timezone.utc).isoformat()
        result = []
        for item in items:
            area_no = str(item.get("areaNo", ""))
            if area_no not in AREA_LOCATIONS:
                continue
            loc = AREA_LOCATIONS[area_no]

            forecast: Dict[str, float] = {}
            for h in hours:
                raw = item.get(f"h{h}")
                if raw is not None:
                    try:
                        forecast[f"h{h}"] = float(raw)
                    except (ValueError, TypeError):
                        pass

            first_key = f"h{hours[0]}" if hours else "h1"

            # date 필드 정규화: 10자리(YYYYMMDDhh) → 12자리(YYYYMMDDHHmm)
            date_str = str(item.get("date", ""))
            if len(date_str) == 10:
                date_str += "00"

            result.append({
                "area_no":       area_no,
                "area_name":     loc["name"],
                "lat":           loc["lat"],
                "lng":           loc["lng"],
                "request_code":  store_code,
                "index_value":   forecast.get(first_key),
                "forecast_json": json.dumps(forecast),
                "published_at":  date_str,
                "synced_at":     synced_at,
            })
        return result

    # ── 더미 데이터 ───────────────────────────────────────────────────────────

    def _mock_data(self, request_code: str) -> List[Dict[str, Any]]:
        synced_at   = datetime.now(timezone.utc).isoformat()
        published_at = self._get_latest_time()

        if request_code == "UV":
            hours  = UV_HOURS
            make   = self._mock_uv_forecast
        elif request_code == "AIR":
            hours  = AIR_HOURS
            make   = self._mock_air_forecast
        else:
            hours  = SENSATION_HOURS
            make   = self._mock_sensation_forecast

        result = []
        for area_no, loc in AREA_LOCATIONS.items():
            forecast = make(hours)
            result.append({
                "area_no":       area_no,
                "area_name":     loc["name"],
                "lat":           loc["lat"],
                "lng":           loc["lng"],
                "request_code":  request_code,
                "index_value":   forecast.get(f"h{hours[0]}"),
                "forecast_json": json.dumps(forecast),
                "published_at":  published_at,
                "synced_at":     synced_at,
            })
        return result

    @staticmethod
    def _mock_sensation_forecast(hours: List[int]) -> Dict[str, float]:
        base = round(random.uniform(28.0, 42.0), 1)
        return {
            f"h{h}": round(
                base + 4 * math.sin((h % 24 - 4) * math.pi / 12) + random.uniform(-0.5, 0.5), 1
            )
            for h in hours
        }

    @staticmethod
    def _mock_uv_forecast(hours: List[int]) -> Dict[str, float]:
        """자외선은 낮에만 수치가 있고 야간은 0."""
        peak = round(random.uniform(3.0, 11.0), 1)
        result = {}
        for h in hours:
            hod = h % 24                                   # 하루 중 시각
            factor = max(0.0, math.sin((hod - 6) * math.pi / 12)) if 6 <= hod <= 18 else 0.0
            result[f"h{h}"] = round(peak * factor + random.uniform(-0.2, 0.2), 1)
            result[f"h{h}"] = max(0.0, result[f"h{h}"])
        return result

    @staticmethod
    def _mock_air_forecast(hours: List[int]) -> Dict[str, float]:
        """대기정체: 25 / 50 / 75 / 100 4단계."""
        levels = [25.0, 50.0, 75.0, 100.0]
        return {f"h{h}": float(random.choice(levels)) for h in hours}

    # ── 유틸 ──────────────────────────────────────────────────────────────────

    def _get_time_daily(self) -> str:
        """UV/AIR: 하루 1회 00:00 발표."""
        return datetime.now(KST).strftime("%Y%m%d") + "0000"

    def _get_time_3hourly(self) -> str:
        """체감온도: 3시간 주기 발표."""
        now  = datetime.now(KST)
        hour = (now.hour // 3) * 3
        return now.strftime(f"%Y%m%d{hour:02d}00")

    def _get_latest_time(self) -> str:
        """더미 데이터용 — 3시간 단위 반환 (mock published_at에 사용)."""
        return self._get_time_3hourly()
