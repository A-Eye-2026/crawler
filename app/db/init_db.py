"""
app/db/init_db.py

DB 초기화 파일

역할:
- SQLAlchemy Base에 등록된 모델들을 기준으로
  실제 DB 테이블을 생성한다.
- 현재는 region, wildfire_risk, disaster_message, collector_job_log 테이블을 생성한다.

실행 예시:
- python -m app.db.init_db
"""

from sqlalchemy import inspect, text

from app.db.base import Base
from app.db.session import engine

# create_all()은 import 되어 Base에 등록된 모델만 생성한다.
from app.db.models.region import Region  # noqa: F401
from app.db.models.wildfire_risk import WildfireRisk  # noqa: F401
from app.db.models.disaster_message import DisasterMessage  # noqa: F401
from app.db.models.collector_job_log import CollectorJobLog  # noqa: F401


def init_db():
    """
    DB 테이블 생성 함수

    역할:
    - Base에 등록된 모든 모델을 실제 DB에 생성한다.
    - 이미 있는 테이블은 그대로 두고,
      없는 테이블만 추가 생성한다.
    """
    print("[START] DB 테이블 생성을 시작합니다.")

    Base.metadata.create_all(bind=engine)
    ensure_schema_updates()

    print("[DONE] DB 테이블 생성이 완료되었습니다.")


def ensure_schema_updates():
    """
    기존 SQLite 파일에도 필요한 신규 컬럼을 안전하게 추가한다.
    """
    inspector = inspect(engine)

    if "collector_job_log" not in inspector.get_table_names():
        return

    existing_columns = {
        column_info["name"]
        for column_info in inspector.get_columns("collector_job_log")
    }

    if "skip_reason_summary" not in existing_columns:
        with engine.begin() as connection:
            # skip_reason 집계를 운영 화면에서 조회할 수 있도록 JSON 텍스트 컬럼을 추가한다.
            connection.execute(
                text(
                    "ALTER TABLE collector_job_log "
                    "ADD COLUMN skip_reason_summary TEXT"
                )
            )


if __name__ == "__main__":
    init_db()
