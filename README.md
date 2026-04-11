# 고속도로 휴게소 실시간 주차 현황 서비스 (MVP)

고속도로 휴게소의 주차 현황을 지도 기반으로 시각화하는 Flask 기반 프로토타입입니다.

## 1. 프로젝트 구조

```bash
restarea_mvp/
├── app.py
├── api_handler.py
├── config.py
├── models.py
├── schema.sql
├── requirements.txt
├── .env.example
├── instance/
├── templates/
│   └── index.html
└── static/
    ├── css/
    │   └── style.css
    └── js/
        └── app.js
```

## 2. 실행 방법

```bash
python -m venv .venv
# macOS / Linux
source .venv/bin/activate
# Windows PowerShell
# .venv\Scripts\Activate.ps1

pip install -r requirements.txt
cp .env.example .env
python app.py
```

브라우저에서 `http://127.0.0.1:5000` 에 접속합니다.

## 3. API 엔드포인트

### GET `/api/v1/parking-status`
휴게소 주차 상태 목록을 JSON으로 반환합니다.

예시 응답:

```json
{
  "count": 3,
  "last_synced_at": "2026-04-11T00:00:00+00:00",
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
      "last_synced_at": "2026-04-11T00:00:00+00:00"
    }
  ]
}
```

## 4. 외부 API 연동 가이드

현재 `api_handler.py`는 다음 전략으로 동작합니다.

1. `EX_API_KEY`가 없으면 mock 데이터를 사용합니다.
2. `EX_API_KEY`가 있으면 실제 API를 호출합니다.
3. 외부 응답을 내부 표준 포맷으로 정규화한 뒤 DB에 upsert 합니다.

실제 공공데이터포털/한국도로공사 응답 필드가 확정되면 `normalize_rest_areas()` 내부 매핑만 수정하면 됩니다.

## 5. 향후 확장 포인트

- APScheduler 또는 Celery를 붙여 주기적 동기화 분리
- SQLite -> PostgreSQL 전환
- 전기차 충전소, 식당 혼잡도, 편의시설 정보 확장
- 프론트엔드 SPA(React/Vue)로 분리
- 인증/권한 및 운영용 관리자 페이지 추가
