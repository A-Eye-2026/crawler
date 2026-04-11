import sqlite3

def check_db():
    try:
        conn = sqlite3.connect('instance/restareas.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        rows = cursor.execute("SELECT name, lat, lng, total_parking_spaces FROM rest_areas LIMIT 10").fetchall()
        
        print(f"\n[DB 데이터 확인 (총 {len(rows)}건 샘플)]")
        if not rows:
            print("데이터가 비어 있습니다.")
            return

        for row in rows:
            print(f"이름: {row['name']} | 좌표: ({row['lat']}, {row['lng']}) | 주차공간: {row['total_parking_spaces']}")
            
    except Exception as e:
        print(f"에러 발생: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    check_db()
