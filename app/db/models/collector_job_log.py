"""
app/db/models/collector_job_log.py

수집 작업 실행 로그 테이블 모델

역할:
- 수집기가 언제 실행됐는지 기록
- 어떤 수집기인지 기록
- 성공/실패 여부 기록
- 몇 건 가져왔고 몇 건 저장했는지 기록
- 에러 메시지 기록

예:
- disaster_message_collector 실행 로그
- wildfire_risk_collector 실행 로그
"""

from datetime import datetime

from sqlalchemy import Column, Integer, String, Text, DateTime

from app.db.base import Base


class CollectorJobLog(Base):
    """
    CollectorJobLog 테이블 모델

    실제 DB 테이블 이름: collector_job_log
    """

    __tablename__ = "collector_job_log"

    """
    id:
    - 기본 키(PK)
    - 자동 증가 정수
    """
    id = Column(Integer, primary_key=True, autoincrement=True)

    """
    job_name:
    - 어떤 수집기인지 이름 저장
    - 예: disaster_message_collector
    - 예: wildfire_risk_collector
    """
    job_name = Column(String(100), nullable=False)

    """
    job_status:
    - 실행 결과 상태
    - 예: STARTED, SUCCESS, FAILED
    - 처음에는 문자열로 단순 관리
    """
    job_status = Column(String(30), nullable=False)

    """
    requested_url:
    - 실제 호출한 API 주소 기록
    - 디버깅할 때 유용
    - 너무 길 수 있으므로 Text 사용
    """
    requested_url = Column(Text, nullable=True)

    """
    response_status_code:
    - 외부 API 응답 상태코드
    - 예: 200, 404, 500
    - API 호출 전 실패면 None일 수 있음
    """
    response_status_code = Column(Integer, nullable=True)

    """
    fetched_count:
    - 외부 API에서 받아온 원본 데이터 개수
    """
    fetched_count = Column(Integer, nullable=True, default=0)

    """
    parsed_count:
    - 파싱 성공 건수
    """
    parsed_count = Column(Integer, nullable=True, default=0)

    """
    saved_count:
    - 실제 DB 저장 성공 건수
    """
    saved_count = Column(Integer, nullable=True, default=0)

    """
    skipped_count:
    - 중복/필터 제외/지역 매핑 실패 등으로 건너뛴 건수
    """
    skipped_count = Column(Integer, nullable=True, default=0)

    """
    error_message:
    - 실패 시 에러 내용 저장
    - 길 수 있으므로 Text 사용
    """
    error_message = Column(Text, nullable=True)

    """
    skip_reason_summary:
    - skip 사유별 집계 결과를 JSON 문자열로 저장
    - 예: {"non_keyword": 31, "duplicate": 19}
    - non_keyword는 정책상 정상 제외라는 점을 운영 화면에서 바로 확인하기 위함
    """
    skip_reason_summary = Column(Text, nullable=True)

    """
    skip_reason_summary:
    - skip 사유별 집계 결과를 JSON 문자열로 저장
    - 예: {"non_keyword": 31, "duplicate": 19}
    - non_keyword는 정책상 정상 제외라는 점을 운영 화면에서 바로 확인하기 위함
    """
    skip_reason_summary = Column(Text, nullable=True)

    """
    started_at:
    - 수집 작업 시작 시각
    """
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    """
    finished_at:
    - 수집 작업 종료 시각
    - 실패해도 종료 시각은 남기는 것이 좋다
    """
    finished_at = Column(DateTime, nullable=True)

    """
    created_at:
    - DB row 생성 시각
    """
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        """
        디버깅용 출력 문자열
        """
        return (
            f"<CollectorJobLog(id={self.id}, "
            f"job_name='{self.job_name}', "
            f"job_status='{self.job_status}')>"
        )
