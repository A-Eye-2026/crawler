import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-key")
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///instance/weather.db")
    WEATHER_API_BASE_URL: str = os.getenv(
        "WEATHER_API_BASE_URL",
        "https://apis.data.go.kr/1360000/LivingWthrIdxServiceV4"
    )
    WEATHER_API_KEY: str = os.getenv("WEATHER_API_KEY", "")
    API_TIMEOUT_SECONDS: int = int(os.getenv("API_TIMEOUT_SECONDS", "10"))
