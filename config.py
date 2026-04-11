import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    """애플리케이션 전역 설정.

    팀 협업을 고려해 환경 변수 기반으로 값을 주입하도록 구성한다.
    추후 SQLite -> PostgreSQL 등으로 바뀌더라도 DATABASE_URL만 바꾸면 되도록 설계했다.
    """

    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-key")
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///instance/restareas.db")
    EX_API_BASE_URL: str = os.getenv(
        "EX_API_BASE_URL",
        "https://data.ex.co.kr/openapi/restinfo/restAreaList"
    )
    EX_API_KEY: str = os.getenv("EX_API_KEY", "")
    API_TIMEOUT_SECONDS: int = int(os.getenv("API_TIMEOUT_SECONDS", "10"))
