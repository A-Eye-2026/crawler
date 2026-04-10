# Wildfire PulseMap

## 프로젝트 개요

`wildfire-pulsemap`은 산불위험예보와 재난문자를 함께 수집해 지도 위에서 보여주는 Flask 기반 펄스맵 프로젝트입니다.  
핵심 목적은 "위험도가 높은 지역"과 "실제로 관련 재난문자가 발송된 지역"을 한 화면에서 확인할 수 있게 만드는 것입니다.

이 프로젝트는 단순한 재난문자 모음 화면이 아니라, 위험 예보 데이터와 실제 문자 데이터를 결합해 산불 대응 관점의 상황 인지 도구를 만드는 데 초점을 둡니다.

## 프로젝트 목표

- 공공데이터 기반으로 산불 위험 지역을 시각화
- 화재/산불 관련 재난문자만 선별 저장
- 수집, 저장, 가공, 시각화를 하나의 흐름으로 연결
- 추후 다른 재난 주제로 확장 가능한 펄스맵 구조 확보

## 현재 구현 범위

- 산불위험예보 API 수집
- 긴급재난문자 API 수집
- 화재/산불 관련 문자 필터링
- 지역 기준 매핑 및 DB 저장
- 실데이터 기반 메인 지도 화면(`/`)
- 최근 수집 로그 확인 화면(`/job-log-test`)
- APScheduler 기반 자동 수집 스케줄

## 재난문자 저장 정책

- 저장 및 표시 대상은 화재/산불 관련 재난문자만 사용합니다.
- 실종자, 호우, 태풍, 산사태, 교통, 생활안전 일반 문자는 저장 대상에서 제외합니다.
- `대피`, `연기`, `통제`, `입산금지`, `소각금지`는 화재/산불 맥락이 함께 있을 때만 저장합니다.
- `non_keyword`는 오류가 아니라 정책상 정상 제외입니다.

## 기술 스택

- Backend: `Python 3`, `Flask`
- Database ORM: `SQLAlchemy`
- Environment: `python-dotenv`
- External API Client: `requests`
- Scheduler: `APScheduler`
- Database: `SQLite`
- Frontend: `Jinja2`, `HTML`, `CSS`, `Vanilla JavaScript`
- Map Rendering: `Leaflet`

## 프로젝트 구조

```text
wildfire-pulsemap/
├─ app/
│  ├─ collectors/      # 외부 API 수집기
│  ├─ db/              # DB 엔진, 초기화, 모델
│  ├─ filters/         # 재난문자 필터링 규칙
│  ├─ static/          # CSS, JS
│  ├─ templates/       # Jinja 템플릿
│  ├─ config.py        # 환경변수 및 공통 설정
│  ├─ routes.py        # 페이지/API 라우트
│  └─ __init__.py      # Flask app factory
├─ scripts/            # 수동 실행, 시드, 분석, 스케줄러 실행 스크립트
├─ storage/            # SQLite DB, lock, backup
├─ run.py              # Flask 개발 서버 실행
└─ README.md
```

## 아키텍처

### 1. 데이터 수집 계층

- `DisasterMessageCollector`
  재난문자 API 호출, 파싱, 지역 매핑, 정책 필터링, DB 저장, 실행 로그 기록을 담당합니다.
- `WildfireRiskCollector`
  산불위험예보 API 호출, 파싱, 지역 매핑, DB 저장, 실행 로그 기록을 담당합니다.

### 2. 데이터 저장 계층

- SQLAlchemy 기반으로 SQLite에 저장합니다.
- `region`을 기준 테이블로 두고 `wildfire_risk`, `disaster_message`가 참조합니다.
- `collector_job_log`는 수집 성공/실패 및 건수 통계를 남깁니다.

### 3. API/서버 계층

- Flask 라우트가 화면과 JSON API를 제공합니다.
- 주요 API:
  - `/api/risk/latest`
  - `/api/messages/latest`

### 4. 프런트 계층

- 메인 페이지 `/`는 Leaflet 지도를 사용합니다.
- 프런트는 `/api/risk/latest`, `/api/messages/latest`를 호출해 실데이터를 렌더링합니다.
- 위험도 마커, 재난문자 마커, 최근 문자 목록, 위험도 TOP 목록을 함께 표시합니다.

### 5. 자동 수집 계층

- `scripts/run_all_collectors.py`에서 APScheduler로 자동 수집을 실행합니다.
- 중복 실행 방지를 위해 lock 파일을 사용합니다.
- 수동 실행 스크립트는 별도로 유지해 로컬 개발 시 즉시 1회 실행이 가능합니다.

## 데이터 흐름

```text
외부 공공 API
  -> collector
  -> 파싱 / 필터링 / 지역 매핑
  -> SQLite 저장
  -> Flask API
  -> Leaflet 기반 펄스맵 화면
```

## DB 설계

### 1. `region`

지역 기준 테이블입니다.  
시도/시군구 단위 지역명과 중심 좌표를 저장하며, 다른 데이터의 기준점 역할을 합니다.

주요 컬럼:

- `id`: PK
- `sido`: 시도명
- `sigungu`: 시군구명
- `region_name`: 전체 지역명
- `region_code`: 행정구역 코드
- `center_lat`, `center_lng`: 지도 중심 좌표

제약:

- `(sido, sigungu)` 유니크

### 2. `wildfire_risk`

산불위험예보 저장 테이블입니다.  
지역별 위험 점수와 위험 등급, 예보 기준 시각을 저장합니다.

주요 컬럼:

- `id`: PK
- `region_id`: `region.id` FK
- `region_name`: 외부 API 원문 지역명
- `risk_score`: 위험 점수
- `risk_level`: 위험 등급
- `forecast_time`: 예보 기준 시각
- `source`: 데이터 출처
- `collected_at`, `created_at`: 수집/생성 시각

제약:

- `(region_id, forecast_time)` 유니크

### 3. `disaster_message`

화재/산불 관련 재난문자 저장 테이블입니다.  
문자 원문, 발송 시각, 지역, 분류 결과를 저장합니다.

주요 컬럼:

- `id`: PK
- `external_message_id`: 외부 문자 ID
- `region_id`: `region.id` FK
- `region_name`: 외부 API 원문 지역명
- `sender`: 발송 기관 또는 발송 구분값
- `message_text`: 문자 본문
- `message_type`: 분류 결과
- `keyword_tag`: 탐지 키워드
- `sent_at`: 발송 시각
- `source`: 데이터 출처
- `collected_at`, `created_at`: 수집/생성 시각

제약:

- `(region_id, sent_at, message_text)` 유니크

### 4. `collector_job_log`

수집 작업 실행 로그 테이블입니다.  
성공/실패 여부, 가져온 건수, 저장 건수, skip 통계를 기록합니다.

주요 컬럼:

- `id`: PK
- `job_name`: 수집기 이름
- `job_status`: `STARTED`, `SUCCESS`, `FAILED`
- `requested_url`: 호출 URL
- `response_status_code`: 응답 코드
- `fetched_count`: 원본 수집 건수
- `parsed_count`: 파싱 성공 건수
- `saved_count`: 저장 성공 건수
- `skipped_count`: 제외/중복/매핑 실패 건수
- `error_message`: 실패 메시지
- `skip_reason_summary`: skip 사유 집계 JSON
- `started_at`, `finished_at`, `created_at`: 작업 시각

## 실행 방법

### 웹 서버 실행

```bash
python run.py
```

접속 URL:

- `http://127.0.0.1:5000/`

### 수동 1회 수집 실행

```bash
python -m scripts.run_disaster_message_collector
python -m scripts.run_wildfire_risk_collector
```

### 자동 수집 스케줄러 실행

```bash
python -m scripts.run_all_collectors
```

## 자동 수집 주기

- 재난문자 collector: 기본 `10분`
- 산불위험예보 collector: 기본 `30분`

`.env`에서 아래 값으로 조정할 수 있습니다.

```env
DISASTER_COLLECTION_INTERVAL_MINUTES=10
WILDFIRE_COLLECTION_INTERVAL_MINUTES=30
```

산불위험예보를 1시간 주기로 바꾸고 싶다면:

```env
WILDFIRE_COLLECTION_INTERVAL_MINUTES=60
```

## 주요 화면

- `/`
  메인 펄스맵 화면
- `/db-test`
  저장 데이터 확인용 테스트 화면
- `/job-log-test`
  collector 실행 로그 확인 화면

## 비고

- 현재 재난문자 정책은 정확도 우선입니다.
- 따라서 저장률을 억지로 높이기보다, 화재/산불 맥락이 분명한 문자만 저장하도록 설계되어 있습니다.

