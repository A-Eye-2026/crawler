"""
app/collectors/wildfire_risk_collector.py

산불위험예보 수집기

역할:
- 외부 산불위험예보 API 호출
- 응답 데이터 파싱
- region 매핑
- wildfire_risk 테이블 저장
- collector_job_log 테이블에 실행 로그 저장

주의:
- 지금 단계는 구조를 먼저 완성하는 단계다.
- 실제 API URL, 파라미터, 응답 필드명은 공공데이터포털 문서에 맞게 나중에 수정하면 된다.
"""

from datetime import datetime
from xml.etree import ElementTree as ET

import requests

from app.config import WILDFIRE_API_KEY, WILDFIRE_API_URL, REQUEST_TIMEOUT
from app.db.session import SessionLocal
from app.db.models.region import Region
from app.db.models.wildfire_risk import WildfireRisk
from app.db.models.collector_job_log import CollectorJobLog


class WildfireRiskCollector:
    """
    산불위험예보 수집기 클래스
    """

    def __init__(self):
        """
        수집기에 필요한 기본 설정값 초기화
        """
        self.api_key = WILDFIRE_API_KEY  # 요청 파라미터에 포함할 인증 키
        self.timeout = REQUEST_TIMEOUT  # 외부 API 지연 시 빠르게 실패하게 하는 제한 시간
        self.base_url = WILDFIRE_API_URL.strip()  # .env에 넣은 실제 산불위험예보 API 주소

        """
        수집 작업 이름
        collector_job_log에 어떤 작업인지 기록할 때 사용
        """
        self.job_name = "wildfire_risk_collector"

    def validate_settings(self):
        """
        실행 전에 필수 설정을 확인해서 설정 오류를 명확히 드러낸다.
        """
        if not self.api_key:
            raise ValueError("WILDFIRE_API_KEY가 비어 있습니다. .env 값을 확인하세요.")

        # 예시 URL이 남아 있으면 DNS 에러 대신 설정 에러로 바로 알려준다.
        if not self.base_url or "example-" in self.base_url:
            raise ValueError(
                "WILDFIRE_API_URL이 비어 있거나 예시 URL입니다. "
                ".env에 실제 산불위험예보 API 주소를 넣어주세요."
            )

    def classify_risk_level(self, risk_score):
        """
        수치형 위험 점수를 화면용 등급 문자열로 바꾼다.
        """
        if risk_score >= 66:
            return "높음"

        if risk_score >= 33:
            return "보통"

        return "낮음"

    def create_job_log(self, session):
        """
        수집 작업 시작 로그 row 생성

        Parameters
        ----------
        session : Session
            DB 세션

        Returns
        -------
        CollectorJobLog
            방금 생성한 로그 객체
        """
        log = CollectorJobLog(
            job_name=self.job_name,
            job_status="STARTED",
            requested_url=self.base_url,
            response_status_code=None,
            fetched_count=0,
            parsed_count=0,
            saved_count=0,
            skipped_count=0,
            error_message=None,
            started_at=datetime.utcnow(),
            finished_at=None,
        )

        session.add(log)
        session.commit()
        session.refresh(log)

        print(f"[LOG] 작업 로그 생성 완료 - log_id={log.id}")

        return log

    def update_job_log_success(
        self,
        session,
        job_log,
        response_status_code,
        fetched_count,
        parsed_count,
        saved_count,
        skipped_count,
    ):
        """
        수집 작업 성공 로그 업데이트
        """
        job_log.job_status = "SUCCESS"
        job_log.response_status_code = response_status_code
        job_log.fetched_count = fetched_count
        job_log.parsed_count = parsed_count
        job_log.saved_count = saved_count
        job_log.skipped_count = skipped_count
        job_log.finished_at = datetime.utcnow()

        session.commit()

        print(f"[LOG] 작업 로그 성공 업데이트 완료 - log_id={job_log.id}")

    def update_job_log_failed(
        self,
        session,
        job_log,
        error_message,
        response_status_code=None,
        fetched_count=0,
        parsed_count=0,
        saved_count=0,
        skipped_count=0,
    ):
        """
        수집 작업 실패 로그 업데이트
        """
        job_log.job_status = "FAILED"
        job_log.response_status_code = response_status_code
        job_log.fetched_count = fetched_count
        job_log.parsed_count = parsed_count
        job_log.saved_count = saved_count
        job_log.skipped_count = skipped_count
        job_log.error_message = error_message
        job_log.finished_at = datetime.utcnow()

        session.commit()

        print(f"[LOG] 작업 로그 실패 업데이트 완료 - log_id={job_log.id}")

    def fetch_risks(self):
        """
        외부 API에서 산불위험예보 원본 데이터를 가져오는 함수

        Returns
        -------
        tuple[list, int | None, str | None]
            (원본 데이터 목록, 응답 상태코드, 에러메시지)
            실패 시 ([], None, 에러문자열)
        """
        print("[START] 산불위험예보 API 호출 시작")

        params = {
            "serviceKey": self.api_key,
            "pageNo": 1,
            "numOfRows": 100,
            "type": "json",
        }

        try:
            self.validate_settings()  # 네트워크 호출 전에 필수 설정부터 검증한다.

            response = requests.get(
                self.base_url,
                params=params,
                timeout=self.timeout,
            )

            print(f"[INFO] 응답 상태코드: {response.status_code}")

            response.raise_for_status()

            root = ET.fromstring(response.text)  # 현재 API는 type=json 요청에도 XML을 반환한다.
            items = []

            for item_elem in root.findall(".//item"):
                item = {child.tag: (child.text or "").strip() for child in item_elem}
                items.append(item)

            print(f"[DONE] 산불위험예보 원본 데이터 수신 완료: {len(items)}건")

            return items, response.status_code, None

        except Exception as e:
            print("[ERROR] 산불위험예보 API 호출 실패")
            print(f"[ERROR DETAIL] {e}")
            return [], None, str(e)

    def parse_risk_item(self, item):
        """
        원본 item 1개를 우리 프로젝트 구조에 맞는 dict로 변환

        Parameters
        ----------
        item : dict
            외부 API 원본 데이터 1건

        Returns
        -------
        dict | None
            저장 가능한 형태의 dict
            파싱 실패 시 None
        """
        try:
            region_name = item.get("doname", "").strip()  # 응답 예시 기준 지역명은 doname에 들어온다.
            risk_score_raw = item.get("std", 0)  # std 값을 대표 위험 점수로 사용한다.
            forecast_time_raw = item.get("analdate", "")

            risk_score = float(risk_score_raw)
            risk_level = self.classify_risk_level(risk_score)  # 화면 표시는 점수 기반 간단 등급으로 보강한다.
            forecast_time = datetime.strptime(forecast_time_raw, "%Y-%m-%d %H")

            return {
                "region_name": region_name,
                "risk_score": risk_score,
                "risk_level": risk_level,
                "forecast_time": forecast_time,
            }

        except Exception as e:
            print("[ERROR] 산불위험예보 파싱 실패")
            print(f"[ERROR DETAIL] {e}")
            print(f"[ERROR ITEM] {item}")
            return None

    def find_region(self, session, region_name):
        """
        region_name 문자열을 기준으로 region 테이블에서 지역 찾기
        """
        return (
            session.query(Region)
            .filter(Region.region_name == region_name)
            .first()
        )

    def is_duplicate(self, session, region_id, forecast_time):
        """
        같은 산불위험예보가 이미 저장되어 있는지 검사

        중복 기준:
        - region_id
        - forecast_time
        """
        existing = (
            session.query(WildfireRisk)
            .filter(
                WildfireRisk.region_id == region_id,
                WildfireRisk.forecast_time == forecast_time,
            )
            .first()
        )

        return existing is not None

    def save_risks(self, parsed_items):
        """
        파싱된 위험도 목록을 DB에 저장

        Returns
        -------
        tuple[int, int]
            (saved_count, skipped_count)
        """
        print("[START] 산불위험예보 DB 저장 시작")

        session = SessionLocal()

        saved_count = 0
        skipped_count = 0

        try:
            for item in parsed_items:
                if not item:
                    skipped_count += 1
                    continue

                region_name = item["region_name"]
                forecast_time = item["forecast_time"]

                """
                1) region 매핑
                """
                region = self.find_region(session, region_name)
                if not region:
                    print(f"[WARN] 지역 매핑 실패: {region_name}")
                    skipped_count += 1
                    continue

                """
                2) 중복 검사
                """
                if self.is_duplicate(session, region.id, forecast_time):
                    print(f"[INFO] 중복 위험도 건너뜀: {region_name} / {forecast_time}")
                    skipped_count += 1
                    continue

                """
                3) DB 저장 객체 생성
                """
                new_risk = WildfireRisk(
                    region_id=region.id,
                    region_name=region.region_name,
                    risk_score=item["risk_score"],
                    risk_level=item["risk_level"],
                    forecast_time=forecast_time,
                    source="wildfire_api"
                )

                session.add(new_risk)
                saved_count += 1

            session.commit()

            print(
                f"[DONE] 산불위험예보 DB 저장 완료 - 저장: {saved_count}, 건너뜀: {skipped_count}"
            )

            return saved_count, skipped_count

        except Exception as e:
            session.rollback()
            print("[ERROR] 산불위험예보 DB 저장 중 오류 발생")
            print(f"[ERROR DETAIL] {e}")
            raise

        finally:
            session.close()
            print("[END] 산불위험예보 DB 세션 종료")

    def collect(self):
        """
        수집기 전체 실행 흐름

        순서:
        1. 작업 로그 생성
        2. API 호출
        3. 원본 파싱
        4. DB 저장
        5. 작업 로그 성공/실패 업데이트
        """
        print("[START] 산불위험예보 수집 작업 시작")

        log_session = SessionLocal()
        job_log = None

        try:
            job_log = self.create_job_log(log_session)

            raw_items, response_status_code, fetch_error = self.fetch_risks()

            """
            API 호출 자체가 실패하면 바로 FAILED 처리
            """
            if fetch_error:
                self.update_job_log_failed(
                    session=log_session,
                    job_log=job_log,
                    error_message=fetch_error,
                    response_status_code=response_status_code,
                    fetched_count=0,
                    parsed_count=0,
                    saved_count=0,
                    skipped_count=0,
                )
                print("[DONE] 산불위험예보 수집 작업 종료 (API 호출 실패)")
                return

            parsed_items = []
            for item in raw_items:
                parsed = self.parse_risk_item(item)
                if parsed:
                    parsed_items.append(parsed)

            parsed_count = len(parsed_items)
            fetched_count = len(raw_items)

            print(f"[INFO] 파싱 완료 건수: {parsed_count}")

            saved_count, skipped_count = self.save_risks(parsed_items)

            self.update_job_log_success(
                session=log_session,
                job_log=job_log,
                response_status_code=response_status_code,
                fetched_count=fetched_count,
                parsed_count=parsed_count,
                saved_count=saved_count,
                skipped_count=skipped_count,
            )

            print("[DONE] 산불위험예보 수집 작업 종료")

        except Exception as e:
            print("[ERROR] 산불위험예보 수집 작업 전체 실패")
            print(f"[ERROR DETAIL] {e}")

            if job_log:
                self.update_job_log_failed(
                    session=log_session,
                    job_log=job_log,
                    error_message=str(e),
                )

        finally:
            log_session.close()
            print("[END] 로그 세션 종료")
