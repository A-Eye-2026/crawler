"""
app/config.py

프로젝트 전역 설정 파일

역할:
- .env 파일에서 환경변수 로드
- DB 연결 주소 관리
- 외부 API 키 관리
- 수집기 공통 설정 관리
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# 프로젝트 루트의 .env를 먼저 읽어 환경별 설정을 주입한다.
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent  # app/ 상위인 프로젝트 루트를 기준 경로로 사용한다.

"""
DATABASE_URL:
- SQLite 또는 나중에 PostgreSQL 주소를 환경변수로 관리
- 환경변수가 없으면 기본값으로 SQLite 사용
"""
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///storage/pulsemap.db")


def resolve_database_url(database_url: str) -> str:
    """
    상대 SQLite 경로를 프로젝트 루트 기준 절대 경로로 고정한다.
    """
    sqlite_prefix = "sqlite:///"

    # PostgreSQL 같은 다른 엔진은 원래 URL을 그대로 사용한다.
    if not database_url.startswith(sqlite_prefix):
        return database_url

    sqlite_path = database_url[len(sqlite_prefix):]

    # 이미 절대 경로면 추가 변환 없이 그대로 사용한다.
    if Path(sqlite_path).is_absolute():
        return database_url

    absolute_path = (BASE_DIR / sqlite_path).resolve()
    return f"{sqlite_prefix}{absolute_path.as_posix()}"


DATABASE_URL = resolve_database_url(DATABASE_URL)  # 어떤 실행 위치에서도 같은 DB 파일을 보도록 정규화한다.

"""
외부 공공데이터 API 키
- 각 수집기가 요청 파라미터에 붙여서 사용한다.
"""
DISASTER_API_KEY = os.getenv("DISASTER_API_KEY", "")
WILDFIRE_API_KEY = os.getenv("WILDFIRE_API_KEY", "")

"""
외부 공공데이터 API URL
- 예시 URL이 아니라 실제 호출 주소를 .env에 넣어야 수집이 동작한다.
"""
DISASTER_API_URL = os.getenv("DISASTER_API_URL", "")
WILDFIRE_API_URL = os.getenv("WILDFIRE_API_URL", "")

"""
REQUEST_TIMEOUT:
- 외부 API 요청 제한 시간(초)
- 환경변수 값이 문자열로 들어오므로 int 변환
"""
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "10"))

"""
자동 수집 스케줄 설정
- 재난문자는 기본 10분 주기
- 산불위험예보는 기본 30분 주기
- 로컬 개발 환경에서도 .env 값만 바꿔 주기를 쉽게 조정할 수 있게 한다.
"""
DISASTER_COLLECTION_INTERVAL_MINUTES = int(
    os.getenv("DISASTER_COLLECTION_INTERVAL_MINUTES", "10")
)
WILDFIRE_COLLECTION_INTERVAL_MINUTES = int(
    os.getenv("WILDFIRE_COLLECTION_INTERVAL_MINUTES", "30")
)
