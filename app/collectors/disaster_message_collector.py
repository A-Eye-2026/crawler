"""
app/collectors/disaster_message_collector.py

긴급재난문자 수집기

역할:
- 외부 재난문자 API 호출
- 응답 데이터 파싱
- 산불/화재 관련 문자만 필터링
- region 매핑
- disaster_message 테이블 저장
- collector_job_log 테이블에 실행 로그 저장

주의:
- 지금 단계는 "구조를 먼저 완성"하는 단계다.
- 실제 API 엔드포인트/파라미터는 발급받은 문서에 맞게 나중에 수정하면 된다.
"""

from datetime import datetime
import json
import time
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import requests

from app.config import DISASTER_API_KEY, DISASTER_API_URL, REQUEST_TIMEOUT
from app.db.session import SessionLocal
from app.db.models.region import Region
from app.db.models.disaster_message import DisasterMessage
from app.db.models.collector_job_log import CollectorJobLog
from app.filters.keyword_filter import (
    contains_disaster_keyword,
    extract_keyword_tag,
    classify_message_type,
)


class DisasterMessageCollector:
    """
    긴급재난문자 수집기 클래스

    왜 클래스로 만드나?
    - 설정값, 요청 함수, 파싱 함수, 저장 함수를 한 객체 안에서 관리하기 쉽다.
    - 나중에 collector가 늘어나도 구조를 맞추기 좋다.
    """

    STORAGE_POLICY_NAME = "fire_wildfire_only"
    SKIP_REASON_KEYS = (
        "non_keyword",
        "duplicate",
        "region_unmatched",
        "parse_error",
        "other",
    )

    def __init__(self):
        """
        수집기에 필요한 기본 설정값 초기화
        """
        self.api_key = DISASTER_API_KEY  # 요청 파라미터에 포함할 인증 키
        self.timeout = REQUEST_TIMEOUT  # 외부 API가 느릴 때 무한 대기하지 않도록 제한
        self.base_url = DISASTER_API_URL.strip()  # .env에 넣은 실제 재난문자 API 주소
        self.max_retries = 3  # 일시적인 연결 reset에 대비해 짧게 재시도한다.

        """
        수집 작업 이름
        collector_job_log에 어떤 작업인지 기록할 때 사용
        """
        self.job_name = "disaster_message_collector"

    def create_skip_reason_counts(self):
        """
        skip_reason 집계를 항상 같은 키 집합으로 초기화한다.
        """
        return {reason_key: 0 for reason_key in self.SKIP_REASON_KEYS}

    def should_store_message(self, message_text):
        """
        펄스맵 정책상 저장할지 여부를 명확히 분리한 함수

        정책:
        - 저장/표시 대상은 화재/산불 관련 문자만
        - non_keyword는 오류가 아니라 정책상 정상 제외다
        """
        if contains_disaster_keyword(message_text):
            return True, None

        return False, "non_keyword"

    def validate_settings(self):
        """
        실행 전에 필수 설정을 확인해서 원인을 빠르게 알 수 있게 한다.
        """
        if not self.api_key:
            raise ValueError("DISASTER_API_KEY가 비어 있습니다. .env 값을 확인하세요.")

        # 예시 URL이 남아 있으면 네트워크 호출 전에 즉시 중단한다.
        if not self.base_url or "example-" in self.base_url:
            raise ValueError(
                "DISASTER_API_URL이 비어 있거나 예시 URL입니다. "
                ".env에 실제 재난문자 API 주소를 넣어주세요."
            )

    def build_request_url(self):
        """
        .env URL에 샘플 query가 섞여 있어도 실제 요청값으로 덮어쓴다.
        """
        parsed = urlparse(self.base_url)
        query = dict(parse_qsl(parsed.query, keep_blank_values=True))

        # .env에 남아 있을 수 있는 sample serviceKey를 실제 키로 교체한다.
        query["serviceKey"] = self.api_key
        query["pageNo"] = "1"
        query["numOfRows"] = "50"
        query["type"] = "json"

        request_url = urlunparse(
            (
                parsed.scheme,
                parsed.netloc,
                parsed.path,
                parsed.params,
                urlencode(query, doseq=True),
                parsed.fragment,
            )
        )
        return request_url

    def create_job_log(self, session):
        """
        수집 작업 시작 로그 row 생성
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
        skip_reason_counts,
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
        job_log.skip_reason_summary = json.dumps(
            skip_reason_counts,
            ensure_ascii=False,
            sort_keys=True,
        )
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
        skip_reason_counts=None,
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
        job_log.skip_reason_summary = json.dumps(
            skip_reason_counts or self.create_skip_reason_counts(),
            ensure_ascii=False,
            sort_keys=True,
        )
        job_log.finished_at = datetime.utcnow()

        session.commit()

        print(f"[LOG] 작업 로그 실패 업데이트 완료 - log_id={job_log.id}")

    def fetch_messages(self):
        """
        외부 API에서 재난문자 원본 데이터를 가져오는 함수

        Returns
        -------
        tuple[list, int | None, str | None]
            (원본 데이터 목록, 응답 상태코드, 에러메시지)
            실패 시 ([], None, 에러문자열)
        """
        print("[START] 재난문자 API 호출 시작")

        try:
            self.validate_settings()  # 잘못된 설정이면 API 호출 전에 바로 실패 원인을 남긴다.
            request_url = self.build_request_url()  # 샘플 query가 섞여 있어도 실제 값으로 정리한다.
            response = None

            for attempt in range(1, self.max_retries + 1):
                try:
                    response = requests.get(
                        request_url,
                        timeout=self.timeout,
                        headers={
                            "User-Agent": "wildfire-pulsemap/1.0",
                            "Accept": "application/json",
                        },
                    )
                    break

                except requests.RequestException as request_error:
                    print(f"[WARN] 재난문자 API 재시도 {attempt}/{self.max_retries} 실패: {request_error}")

                    if attempt == self.max_retries:
                        raise

                    time.sleep(1)  # 짧게 쉬고 다시 붙어 일시적 reset을 흡수한다.

            print(f"[INFO] 응답 상태코드: {response.status_code}")

            response.raise_for_status()

            data = response.json()

            # safetydata 응답은 body 배열에 실제 데이터가 들어온다.
            items = data.get("body", [])

            print(f"[DONE] 재난문자 원본 데이터 수신 완료: {len(items)}건")
            return items, response.status_code, None

        except Exception as e:
            print("[ERROR] 재난문자 API 호출 실패")
            print(f"[ERROR DETAIL] {e}")
            return [], None, str(e)

    def parse_message_item(self, item):
        """
        원본 item 1개를 우리 프로젝트 구조에 맞는 dict로 변환
        """
        try:
            region_name = item.get("RCPTN_RGN_NM", "").strip()  # 수신 지역명
            sender = item.get("DST_SE_NM", "").strip()  # 데이터에 기관명 대신 분류값이 먼저 오므로 임시로 저장
            message_text = item.get("MSG_CN", "").strip()  # 실제 재난문자 본문
            external_message_id = item.get("SN", None)  # 제공 데이터의 고유 일련번호
            sent_at_raw = item.get("CRT_DT", "")

            sent_at = datetime.strptime(sent_at_raw, "%Y/%m/%d %H:%M:%S")

            return {
                "external_message_id": external_message_id,
                "region_name": region_name,
                "sender": sender,
                "message_text": message_text,
                "sent_at": sent_at,
            }

        except Exception as e:
            print("[ERROR] 재난문자 파싱 실패")
            print(f"[ERROR DETAIL] {e}")
            print(f"[ERROR ITEM] {item}")
            return None

    def normalize_region_text(self, region_text):
        """
        공백과 과거 시도 명칭을 정리해서 DB 매칭에 쓰기 좋게 만든다.
        """
        normalized_text = " ".join(region_text.replace(",", " , ").split())

        replacements = {
            "전라북도": "전북특별자치도",
            "강원도": "강원특별자치도",
        }

        for before_text, after_text in replacements.items():
            normalized_text = normalized_text.replace(before_text, after_text)

        local_aliases = {
            "부산광역시 진구": "부산광역시 부산진구",
        }

        # 일부 수신 지역은 구 이름이 축약되어 와서 대표 행정구역명으로 보정한다.
        for before_text, after_text in local_aliases.items():
            normalized_text = normalized_text.replace(before_text, after_text)

        return normalized_text.strip()

    def extract_region_candidates(self, region_name):
        """
        재난문자 수신 지역 문자열에서 exact/sigungu/sido 후보를 순서대로 만든다.
        """
        normalized_region_name = self.normalize_region_text(region_name)
        first_region_segment = normalized_region_name.split(",")[0].strip()  # 다지역 문자는 첫 지역을 대표값으로 사용한다.
        first_region_segment = first_region_segment.replace(" 전체", "").strip()
        tokens = first_region_segment.split()

        candidates = []

        if first_region_segment:
            candidates.append(first_region_segment)

        if len(tokens) >= 2:
            second_token = tokens[1]

            # 시/군/구 단위까지 포함된 대표 region_name 후보를 만든다.
            if second_token.endswith(("시", "군", "구")):
                candidates.append(f"{tokens[0]} {second_token}")

        if tokens:
            candidates.append(tokens[0])

        seen_candidates = []
        for candidate in candidates:
            if candidate and candidate not in seen_candidates:
                seen_candidates.append(candidate)

        return seen_candidates

    def extract_sido_name(self, region_name):
        """
        재난문자 수신 지역 문자열에서 가장 먼저 보이는 시도명을 추출한다.
        """
        normalized_region_name = self.normalize_region_text(region_name)

        sido_names = [
            "서울특별시",
            "부산광역시",
            "대구광역시",
            "인천광역시",
            "광주광역시",
            "대전광역시",
            "울산광역시",
            "세종특별자치시",
            "경기도",
            "강원특별자치도",
            "충청북도",
            "충청남도",
            "전북특별자치도",
            "전라북도",
            "전라남도",
            "경상북도",
            "경상남도",
            "제주특별자치도",
            "전국",
        ]

        cleaned_region_name = normalized_region_name.replace(" ", "")

        # 여러 지역이 콤마로 섞여 와도 첫 번째로 식별되는 시도명을 사용한다.
        for sido_name in sido_names:
            if sido_name.replace(" ", "") in cleaned_region_name:
                return sido_name

        return None

    def find_region(self, session, region_name):
        """
        region_name 문자열을 기준으로 region 테이블에서 지역 찾기
        """
        for candidate in self.extract_region_candidates(region_name):
            exact_region = (
                session.query(Region)
                .filter(Region.region_name == candidate)
                .first()
            )

            if exact_region:
                return exact_region

        sido_name = self.extract_sido_name(region_name)
        if not sido_name:
            return None

        # 시군구까지 일치하지 않는 문자는 시도 기준 대표 region으로 매핑한다.
        return (
            session.query(Region)
            .filter(Region.region_name == sido_name)
            .first()
        )

    def is_duplicate(self, session, region_id, sent_at, message_text):
        """
        같은 재난문자가 이미 저장되어 있는지 검사
        """
        existing = (
            session.query(DisasterMessage)
            .filter(
                DisasterMessage.region_id == region_id,
                DisasterMessage.sent_at == sent_at,
                DisasterMessage.message_text == message_text,
            )
            .first()
        )

        return existing is not None

    def save_messages(self, parsed_items, skip_reason_counts):
        """
        파싱된 메시지 목록을 DB에 저장

        Returns
        -------
        tuple[int, int]
            (saved_count, skipped_count)
        """
        print("[START] 재난문자 DB 저장 시작")

        session = SessionLocal()

        saved_count = 0
        skipped_count = 0

        try:
            for item in parsed_items:
                if not item:
                    skip_reason_counts["other"] += 1
                    skipped_count += 1
                    continue

                region_name = item["region_name"]
                message_text = item["message_text"]
                sent_at = item["sent_at"]

                should_store, skip_reason = self.should_store_message(message_text)
                if not should_store:
                    skip_reason_counts[skip_reason] += 1  # non_keyword는 정책상 정상 제외다.
                    skipped_count += 1
                    continue

                region = self.find_region(session, region_name)
                if not region:
                    skip_reason_counts["region_unmatched"] += 1
                    print(f"[WARN] 지역 매핑 실패: {region_name}")
                    skipped_count += 1
                    continue

                if self.is_duplicate(session, region.id, sent_at, message_text):
                    skip_reason_counts["duplicate"] += 1
                    print(f"[INFO] 중복 문자 건너뜀: {region_name} / {sent_at}")
                    skipped_count += 1
                    continue

                keyword_tag = extract_keyword_tag(message_text)
                message_type = classify_message_type(message_text)

                new_message = DisasterMessage(
                    external_message_id=item["external_message_id"],
                    region_id=region.id,
                    region_name=region.region_name,
                    sender=item["sender"],
                    message_text=message_text,
                    message_type=message_type,
                    keyword_tag=keyword_tag,
                    sent_at=sent_at,
                    source="disaster_api"
                )

                session.add(new_message)
                saved_count += 1

            session.commit()

            print(
                f"[DONE] 재난문자 DB 저장 완료 - 저장: {saved_count}, 건너뜀: {skipped_count}"
            )

            return saved_count, skipped_count, skip_reason_counts

        except Exception as e:
            session.rollback()
            print("[ERROR] 재난문자 DB 저장 중 오류 발생")
            print(f"[ERROR DETAIL] {e}")
            raise

        finally:
            session.close()
            print("[END] 재난문자 DB 세션 종료")

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
        print("[START] 재난문자 수집 작업 시작")

        log_session = SessionLocal()
        job_log = None

        try:
            job_log = self.create_job_log(log_session)
            skip_reason_counts = self.create_skip_reason_counts()

            raw_items, response_status_code, fetch_error = self.fetch_messages()

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
                    skip_reason_counts=skip_reason_counts,
                )
                print("[DONE] 재난문자 수집 작업 종료 (API 호출 실패)")
                return

            parsed_items = []
            for item in raw_items:
                parsed = self.parse_message_item(item)
                if parsed:
                    parsed_items.append(parsed)
                else:
                    skip_reason_counts["parse_error"] += 1  # 파싱 실패는 정책 제외가 아니라 입력 해석 실패다.

            parsed_count = len(parsed_items)
            fetched_count = len(raw_items)
            skipped_count = skip_reason_counts["parse_error"]

            print(f"[INFO] 파싱 완료 건수: {parsed_count}")

            saved_count, save_skipped_count, skip_reason_counts = self.save_messages(
                parsed_items,
                skip_reason_counts,
            )
            skipped_count += save_skipped_count

            self.update_job_log_success(
                session=log_session,
                job_log=job_log,
                response_status_code=response_status_code,
                fetched_count=fetched_count,
                parsed_count=parsed_count,
                saved_count=saved_count,
                skipped_count=skipped_count,
                skip_reason_counts=skip_reason_counts,
            )

            print("[DONE] 재난문자 수집 작업 종료")

        except Exception as e:
            print("[ERROR] 재난문자 수집 작업 전체 실패")
            print(f"[ERROR DETAIL] {e}")

            if job_log:
                self.update_job_log_failed(
                    session=log_session,
                    job_log=job_log,
                    error_message=str(e),
                    skip_reason_counts=skip_reason_counts if "skip_reason_counts" in locals() else self.create_skip_reason_counts(),
                )

        finally:
            log_session.close()
            print("[END] 로그 세션 종료")
