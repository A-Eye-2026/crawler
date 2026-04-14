import os

from flask import Flask, jsonify, render_template, request

from api_handler import LivingWeatherAPIClient, REQUEST_CODE_LABELS
from config import Config
from models import Database

config = Config()
app = Flask(__name__)
app.config["SECRET_KEY"] = config.SECRET_KEY

db = Database(config.DATABASE_URL)
api_client = LivingWeatherAPIClient(
    base_url=config.WEATHER_API_BASE_URL,
    api_key=config.WEATHER_API_KEY,
    timeout_seconds=config.API_TIMEOUT_SECONDS,
)

DEFAULT_REQUEST_CODE = "A42"


# ── 데이터 동기화 ────────────────────────────────────────────────────────────

def _sync(request_code: str) -> None:
    try:
        rows = api_client.fetch_and_normalize(request_code)
        if rows:
            db.upsert_weather_indices(rows)
            print(f"[*] {request_code}({REQUEST_CODE_LABELS[request_code]}): {len(rows)}개 지역 동기화 완료")
        else:
            print(f"[!] {request_code}: 수신 데이터 0건")
    except Exception as exc:
        app.logger.warning("동기화 실패 [%s]: %s", request_code, exc)


def _sync_all() -> None:
    """모든 requestCode 일괄 동기화 (스케줄러 전용)."""
    print("[스케줄러] 자동 동기화 시작")
    for code in REQUEST_CODE_LABELS:
        _sync(code)
    print("[스케줄러] 자동 동기화 완료")


# ── 앱 초기화 ────────────────────────────────────────────────────────────────

def bootstrap() -> None:
    db.init_db()
    if config.WEATHER_API_KEY:
        print(f"[*] API 키 확인 (Key: {config.WEATHER_API_KEY[:4]}***)")
    else:
        print("[!] WEATHER_API_KEY 없음 → 더미 데이터로 초기화")
    _sync(DEFAULT_REQUEST_CODE)


# ── 스케줄러 (3시간 주기 자동 동기화) ───────────────────────────────────────

def _start_scheduler():
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        scheduler = BackgroundScheduler(daemon=True)
        scheduler.add_job(_sync_all, "interval", hours=3, id="auto_sync")
        scheduler.start()
        print("[스케줄러] 3시간 주기 자동 동기화 활성화")
        return scheduler
    except ImportError:
        print("[!] APScheduler 미설치 → 자동 동기화 비활성화")
        return None


# ── 라우트 ───────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html", request_codes=REQUEST_CODE_LABELS)


@app.route("/api/v1/weather-index")
def weather_index():
    code = request.args.get("requestCode", DEFAULT_REQUEST_CODE)
    if code not in REQUEST_CODE_LABELS:
        return jsonify({"error": "유효하지 않은 requestCode"}), 400

    rows = db.get_weather_indices(code)
    if not rows:
        _sync(code)
        rows = db.get_weather_indices(code)

    return jsonify({
        "request_code": code,
        "label": REQUEST_CODE_LABELS[code],
        "count": len(rows),
        "last_synced_at": db.get_last_sync_time(code),
        "items": rows,
    })


@app.route("/api/v1/sync")
def sync():
    code = request.args.get("requestCode", DEFAULT_REQUEST_CODE)
    if code not in REQUEST_CODE_LABELS:
        return jsonify({"error": "유효하지 않은 requestCode"}), 400
    _sync(code)
    rows = db.get_weather_indices(code)
    return jsonify({
        "request_code": code,
        "label": REQUEST_CODE_LABELS[code],
        "count": len(rows),
        "last_synced_at": db.get_last_sync_time(code),
        "items": rows,
    })


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


# ── 진입점 ───────────────────────────────────────────────────────────────────

bootstrap()

# Flask 개발 서버 reloader 환경에서 스케줄러 중복 실행 방지
if not app.debug or os.environ.get("WERKZEUG_RUN_MAIN") == "true":
    _start_scheduler()

if __name__ == "__main__":
    app.run(debug=True)
