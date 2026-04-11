from flask import Flask, jsonify, render_template, request

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
    
    # [주의] 기존 데이터를 삭제하고 다시 받습니다 (테스트용)
    with db.connection() as conn:
        conn.execute("DELETE FROM rest_areas")
    
    if config.EX_API_KEY:
        print(f"[*] API 동기화 시작 (Key: {config.EX_API_KEY[:4]}***)")
        seed_or_refresh_data()
        
        # 실제 DB에 저장된 최종 건수 확인
        final_rows = db.get_rest_areas()
        print(f"[*] 최종: DB에 총 {len(final_rows)}개의 휴게소가 로드되었습니다.")
    else:
        print("[!] API 키가 없어 더미 데이터를 사용합니다.")
        seed_or_refresh_data()


def seed_or_refresh_data() -> None:
    """외부 API 데이터를 가져와 DB에 반영한다."""
    try:
        rest_areas = api_client.fetch_and_normalize()
        if rest_areas:
            db.upsert_rest_areas(rest_areas)
            print(f"[*] 성공: {len(rest_areas)}개의 휴게소 데이터를 동기화했습니다.")
            
            # [디버그] 저장된 데이터 샘플 확인
            rows = db.get_rest_areas()
            if rows:
                print(f"[*] 데이터 샘플: {rows[0]['name']} -> 좌표: {rows[0]['lat']}, {rows[0]['lng']}")
        else:
            print("[!] 경고: API로부터 가져온 데이터가 0건입니다. (응답 구조를 확인하세요)")
    except Exception as exc:
        app.logger.warning("데이터 동기화에 실패했습니다: %s", exc)
        print(f"[!] 에러: 데이터 동기화 중 오류 발생: {exc}")


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


@app.route("/api/v1/search")
def search_rest_areas():
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify({"count": 0, "items": []})

    rows = db.search_rest_areas(query)
    return jsonify(
        {
            "count": len(rows),
            "items": rows,
        }
    )


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


bootstrap()

if __name__ == "__main__":
    app.run(debug=True)
