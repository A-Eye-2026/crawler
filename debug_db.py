import sqlite3


def check_db():
    try:
        conn = sqlite3.connect('instance/weather.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        rows = cursor.execute(
            "SELECT area_name, lat, lng, request_code, index_value FROM weather_indices LIMIT 10"
        ).fetchall()

        print(f"\n[DB 데이터 확인 (총 {len(rows)}건 샘플)]")
        if not rows:
            print("데이터가 비어 있습니다.")
            return

        for row in rows:
            print(
                f"지역: {row['area_name']} | "
                f"좌표: ({row['lat']}, {row['lng']}) | "
                f"코드: {row['request_code']} | "
                f"지수: {row['index_value']}"
            )
    except Exception as e:
        print(f"에러 발생: {e}")
    finally:
        conn.close()


if __name__ == "__main__":
    check_db()
