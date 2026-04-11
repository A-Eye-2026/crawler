from flask import Flask, jsonify, render_template

from api_handler import RestAreaAPIClient
from config import Config
from models import Database


config = Config()
app = Flask(__name__)
app.config["SECRET_KEY"] = config.SECRET_KEY

# 모듈 경계를 분리해두면 추후 의존성 주입 형태로 교체하기 쉽다.
db = Database(config.DATABASE_URL)
api_client = RestAreaAPIClient(
    base_url=config.EX_API_BASE_URL,
    api_key=config.EX_API_KEY,
    timeout_seconds=config.API_TIMEOUT_SECONDS,
)


def bootstrap() -> None:
    """앱 시작 시 필요한 초기화를 수행한다."""
    db.init_db()
    seed_or_refresh_data()


def seed_or_refresh_data() -> None:
    """외부 API 데이터를 가져와 DB에 반영한다.

    - 예외가 발생해도 최소한 기존 DB 데이터는 유지된다.
    - 운영 단계에서는 스케줄러(Cron, APScheduler, Celery Beat 등)로 분리 권장.
    """
    try:
        rest_areas = api_client.fetch_and_normalize()
        if rest_areas:
            db.upsert_rest_areas(rest_areas)
    except Exception as exc:
        app.logger.warning("데이터 동기화에 실패했습니다: %s", exc)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/v1/parking-status")
def parking_status():
    rows = db.get_rest_areas()
    return jsonify(
        {
            "count": len(rows),
            "last_synced_at": db.get_last_sync_time(),
            "items": rows,
        }
    )


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


bootstrap()

if __name__ == "__main__":
    app.run(debug=True)
