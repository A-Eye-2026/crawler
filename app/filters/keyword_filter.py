"""
app/filters/keyword_filter.py

재난문자 본문에서 산불/화재 관련 키워드를 판별하는 필터 파일

역할:
- 긴급재난문자 전체 중에서 산불/화재 관련 문자만 골라내기
- 대피/연기/통제는 산불/화재 맥락이 함께 있을 때만 포함하기
- 문자 유형(message_type)과 키워드(keyword_tag) 분류에 사용

이 파일은 나중에 collector에서 재난문자 본문을 읽은 뒤
저장할지 말지 결정하는 핵심 로직이 된다.
"""

"""
정책 설명:
- 산불/화재는 직접 저장 대상이다.
- 대피/연기/통제/입산금지/소각금지는 산불/화재 맥락이 같이 있을 때만 저장 대상이다.
- 실종자, 호우, 태풍, 산사태, 교통, 생활안전 일반 문자는 non_keyword로 정상 제외한다.
"""
PRIMARY_FIRE_KEYWORDS = [
    "산불",
    "화재",
]

"""
행동/상황 키워드 설명:
- 이 단어들만으로는 저장하지 않는다.
- 산불/화재 맥락과 함께 등장할 때만 저장 대상으로 본다.
"""
FIRE_CONTEXT_ACTION_KEYWORDS = [
    "대피",
    "통제",
    "입산금지",
    "연기",
    "소각금지",
]

"""
산불/화재 맥락 키워드 설명:
- 대피/연기/통제 문자가 실제 화재 문맥인지 판단할 때 보조 기준으로 사용한다.
"""
FIRE_CONTEXT_HINT_KEYWORDS = [
    "산불",
    "화재",
    "불",
    "불길",
    "연소",
    "발화",
    "확산",
]


def contains_disaster_keyword(message_text: str) -> bool:
    """
    문자 본문이 산불/화재 저장 정책을 만족하는지 판별하는 함수

    Parameters
    ----------
    message_text : str
        재난문자 본문

    Returns
    -------
    bool
        저장 대상이면 True, 아니면 False
    """
    # None 방지
    if not message_text:
        return False

    # 양쪽 공백 제거
    text = message_text.strip()

    # 산불/화재 직접 키워드는 바로 저장 대상이다.
    for keyword in PRIMARY_FIRE_KEYWORDS:
        if keyword in text:
            return True

    has_action_keyword = any(keyword in text for keyword in FIRE_CONTEXT_ACTION_KEYWORDS)
    has_fire_context = any(keyword in text for keyword in FIRE_CONTEXT_HINT_KEYWORDS)

    # 대피/통제/연기 문자는 산불/화재 맥락이 있을 때만 저장 대상으로 본다.
    if has_action_keyword and has_fire_context:
        return True

    return False


def extract_keyword_tag(message_text: str) -> str | None:
    """
    문자 본문에서 실제 탐지된 키워드를 하나 반환하는 함수

    예:
    - "[산불] 강릉시 주민 대피 바랍니다" -> "산불"
    - "화재 확산 우려로 통제 중" -> "화재"

    가장 먼저 발견된 키워드 하나를 반환한다.
    없으면 None 반환
    """
    if not message_text:
        return None

    text = message_text.strip()

    for keyword in PRIMARY_FIRE_KEYWORDS:
        if keyword in text:
            return keyword

    for keyword in FIRE_CONTEXT_ACTION_KEYWORDS:
        if keyword in text and contains_disaster_keyword(text):
            return keyword

    return None


def classify_message_type(message_text: str) -> str | None:
    """
    문자 본문을 간단한 유형으로 분류하는 함수

    규칙:
    - "산불" 포함 -> "산불"
    - "화재" 포함 -> "화재"
    - "대피" 포함 + 산불/화재 맥락 -> "대피"
    - "통제" 포함 + 산불/화재 맥락 -> "통제"
    - "연기" 포함 + 산불/화재 맥락 -> "연기"
    - 그 외 저장 정책을 만족하면 "기타"

    Returns
    -------
    str | None
        분류 결과 문자열
    """
    if not message_text:
        return None

    text = message_text.strip()

    if "산불" in text:
        return "산불"

    if "화재" in text:
        return "화재"

    if "대피" in text and contains_disaster_keyword(text):
        return "대피"

    if "통제" in text and contains_disaster_keyword(text):
        return "통제"

    if "연기" in text and contains_disaster_keyword(text):
        return "연기"

    if contains_disaster_keyword(text):
        return "기타"

    return None
