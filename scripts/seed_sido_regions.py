"""
scripts/seed_sido_regions.py

전국 시도/시군구 기준 region 시드 데이터 입력 스크립트
"""

from app.db.models.region import Region
from app.db.session import SessionLocal


SIDO_REGIONS = [
    {"sido": "서울특별시", "sigungu": "전체", "region_name": "서울특별시", "region_code": "11", "center_lat": 37.5665, "center_lng": 126.9780},
    {"sido": "부산광역시", "sigungu": "전체", "region_name": "부산광역시", "region_code": "26", "center_lat": 35.1796, "center_lng": 129.0756},
    {"sido": "대구광역시", "sigungu": "전체", "region_name": "대구광역시", "region_code": "27", "center_lat": 35.8714, "center_lng": 128.6014},
    {"sido": "인천광역시", "sigungu": "전체", "region_name": "인천광역시", "region_code": "28", "center_lat": 37.4563, "center_lng": 126.7052},
    {"sido": "광주광역시", "sigungu": "전체", "region_name": "광주광역시", "region_code": "29", "center_lat": 35.1595, "center_lng": 126.8526},
    {"sido": "대전광역시", "sigungu": "전체", "region_name": "대전광역시", "region_code": "30", "center_lat": 36.3504, "center_lng": 127.3845},
    {"sido": "울산광역시", "sigungu": "전체", "region_name": "울산광역시", "region_code": "31", "center_lat": 35.5384, "center_lng": 129.3114},
    {"sido": "세종특별자치시", "sigungu": "전체", "region_name": "세종특별자치시", "region_code": "36", "center_lat": 36.4800, "center_lng": 127.2890},
    {"sido": "경기도", "sigungu": "전체", "region_name": "경기도", "region_code": "41", "center_lat": 37.4138, "center_lng": 127.5183},
    {"sido": "강원특별자치도", "sigungu": "전체", "region_name": "강원특별자치도", "region_code": "51", "center_lat": 37.8228, "center_lng": 128.1555},
    {"sido": "충청북도", "sigungu": "전체", "region_name": "충청북도", "region_code": "43", "center_lat": 36.6358, "center_lng": 127.4917},
    {"sido": "충청남도", "sigungu": "전체", "region_name": "충청남도", "region_code": "44", "center_lat": 36.5184, "center_lng": 126.8000},
    {"sido": "전북특별자치도", "sigungu": "전체", "region_name": "전북특별자치도", "region_code": "52", "center_lat": 35.7175, "center_lng": 127.1530},
    {"sido": "전라남도", "sigungu": "전체", "region_name": "전라남도", "region_code": "46", "center_lat": 34.8161, "center_lng": 126.4630},
    {"sido": "경상북도", "sigungu": "전체", "region_name": "경상북도", "region_code": "47", "center_lat": 36.4919, "center_lng": 128.8889},
    {"sido": "경상남도", "sigungu": "전체", "region_name": "경상남도", "region_code": "48", "center_lat": 35.4606, "center_lng": 128.2132},
    {"sido": "제주특별자치도", "sigungu": "전체", "region_name": "제주특별자치도", "region_code": "50", "center_lat": 33.4996, "center_lng": 126.5312},
    {"sido": "전국", "sigungu": "전체", "region_name": "전국", "region_code": "00", "center_lat": 36.5, "center_lng": 127.8},
]

SIGUNGU_BY_SIDO = {
    "서울특별시": ["종로구", "중구", "용산구", "성동구", "광진구", "동대문구", "중랑구", "성북구", "강북구", "도봉구", "노원구", "은평구", "서대문구", "마포구", "양천구", "강서구", "구로구", "금천구", "영등포구", "동작구", "관악구", "서초구", "강남구", "송파구", "강동구"],
    "부산광역시": ["중구", "서구", "동구", "영도구", "부산진구", "동래구", "남구", "북구", "해운대구", "사하구", "금정구", "강서구", "연제구", "수영구", "사상구", "기장군"],
    "대구광역시": ["중구", "동구", "서구", "남구", "북구", "수성구", "달서구", "달성군", "군위군"],
    "인천광역시": ["중구", "동구", "미추홀구", "연수구", "남동구", "부평구", "계양구", "서구", "강화군", "옹진군"],
    "광주광역시": ["동구", "서구", "남구", "북구", "광산구"],
    "대전광역시": ["동구", "중구", "서구", "유성구", "대덕구"],
    "울산광역시": ["중구", "남구", "동구", "북구", "울주군"],
    "세종특별자치시": [],
    "경기도": ["수원시 장안구", "수원시 권선구", "수원시 팔달구", "수원시 영통구", "성남시 수정구", "성남시 중원구", "성남시 분당구", "의정부시", "안양시 만안구", "안양시 동안구", "부천시", "광명시", "평택시", "동두천시", "안산시 상록구", "안산시 단원구", "고양시 덕양구", "고양시 일산동구", "고양시 일산서구", "과천시", "구리시", "남양주시", "오산시", "시흥시", "군포시", "의왕시", "하남시", "용인시 처인구", "용인시 기흥구", "용인시 수지구", "파주시", "이천시", "안성시", "김포시", "화성시", "광주시", "양주시", "포천시", "여주시", "연천군", "가평군", "양평군"],
    "강원특별자치도": ["춘천시", "원주시", "강릉시", "동해시", "태백시", "속초시", "삼척시", "홍천군", "횡성군", "영월군", "평창군", "정선군", "철원군", "화천군", "양구군", "인제군", "고성군", "양양군"],
    "충청북도": ["청주시 상당구", "청주시 서원구", "청주시 흥덕구", "청주시 청원구", "충주시", "제천시", "보은군", "옥천군", "영동군", "증평군", "진천군", "괴산군", "음성군", "단양군"],
    "충청남도": ["천안시 동남구", "천안시 서북구", "공주시", "보령시", "아산시", "서산시", "논산시", "계룡시", "당진시", "금산군", "부여군", "서천군", "청양군", "홍성군", "예산군", "태안군"],
    "전북특별자치도": ["전주시 완산구", "전주시 덕진구", "군산시", "익산시", "정읍시", "남원시", "김제시", "완주군", "진안군", "무주군", "장수군", "임실군", "순창군", "고창군", "부안군"],
    "전라남도": ["목포시", "여수시", "순천시", "나주시", "광양시", "담양군", "곡성군", "구례군", "고흥군", "보성군", "화순군", "장흥군", "강진군", "해남군", "영암군", "무안군", "함평군", "영광군", "장성군", "완도군", "진도군", "신안군"],
    "경상북도": ["포항시 남구", "포항시 북구", "경주시", "김천시", "안동시", "구미시", "영주시", "영천시", "상주시", "문경시", "경산시", "의성군", "청송군", "영양군", "영덕군", "청도군", "고령군", "성주군", "칠곡군", "예천군", "봉화군", "울진군", "울릉군"],
    "경상남도": ["창원시 의창구", "창원시 성산구", "창원시 마산합포구", "창원시 마산회원구", "창원시 진해구", "진주시", "통영시", "사천시", "김해시", "밀양시", "거제시", "양산시", "의령군", "함안군", "창녕군", "고성군", "남해군", "하동군", "산청군", "함양군", "거창군", "합천군"],
    "제주특별자치도": ["제주시", "서귀포시"],
    "전국": [],
}


def build_sigungu_regions():
    """
    시도별 시군구 목록을 region row 형태로 변환한다.
    """
    sigungu_regions = []

    for sido_name, sigungu_names in SIGUNGU_BY_SIDO.items():
        for index, sigungu_name in enumerate(sigungu_names, start=1):
            sigungu_regions.append(
                {
                    "sido": sido_name,
                    "sigungu": sigungu_name,
                    "region_name": f"{sido_name} {sigungu_name}",
                    "region_code": None,
                    "center_lat": None,
                    "center_lng": None,
                }
            )

    return sigungu_regions


def main():
    """
    시도/시군구 기준 대표 region을 upsert해서 collector 매핑 기준으로 사용한다.
    """
    session = SessionLocal()

    inserted_count = 0
    updated_count = 0

    try:
        all_region_rows = SIDO_REGIONS + build_sigungu_regions()

        for region_data in all_region_rows:
            region = (
                session.query(Region)
                .filter(
                    Region.sido == region_data["sido"],
                    Region.sigungu == region_data["sigungu"],
                )
                .first()
            )

            if region:
                region.region_name = region_data["region_name"]  # 표준 region_name을 최신 값으로 맞춘다.
                region.region_code = region_data["region_code"]
                region.center_lat = region_data["center_lat"]
                region.center_lng = region_data["center_lng"]
                updated_count += 1
                continue

            session.add(Region(**region_data))
            inserted_count += 1

        session.commit()
        print(f"SEEDED inserted={inserted_count} updated={updated_count}")

    except Exception:
        session.rollback()
        raise

    finally:
        session.close()


if __name__ == "__main__":
    main()
