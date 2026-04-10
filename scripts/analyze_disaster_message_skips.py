"""
scripts/analyze_disaster_message_skips.py

재난문자 수집 결과를 skip 사유와 지역 패턴별로 분석하는 스크립트
"""

from collections import Counter, defaultdict

from app.collectors.disaster_message_collector import DisasterMessageCollector
from app.db.session import SessionLocal
from app.filters.keyword_filter import contains_disaster_keyword


def main():
    """
    현재 API 응답 50건을 기준으로 save/skip 사유를 분류한다.
    """
    collector = DisasterMessageCollector()
    raw_items, response_status_code, fetch_error = collector.fetch_messages()

    print(
        f"FETCH status={response_status_code} "
        f"error={fetch_error} count={len(raw_items)}"
    )

    if fetch_error:
        return

    reason_counter = Counter()
    pattern_counter = Counter()
    examples = defaultdict(list)

    session = SessionLocal()

    try:
        for raw_item in raw_items:
            parsed_item = collector.parse_message_item(raw_item)

            if not parsed_item:
                reason_counter["parse_fail"] += 1
                continue

            region_name = collector.normalize_region_text(parsed_item["region_name"])
            message_text = parsed_item["message_text"]
            sent_at = parsed_item["sent_at"]

            if not contains_disaster_keyword(message_text):
                reason = "non_keyword"
            else:
                region = collector.find_region(session, parsed_item["region_name"])

                if not region:
                    reason = "region_unmatched"
                elif collector.is_duplicate(
                    session,
                    region.id,
                    sent_at,
                    message_text,
                ):
                    reason = "duplicate"
                else:
                    reason = "savable"

            reason_counter[reason] += 1
            pattern_counter[(reason, region_name)] += 1

            if len(examples[(reason, region_name)]) < 2:
                examples[(reason, region_name)].append(message_text)

        print("REASONS")
        for reason, count in reason_counter.items():
            print(f"{reason}: {count}")

        print("PATTERNS")
        for (reason, region_name), count in pattern_counter.most_common():
            print(f"{reason}: {count} | {region_name}")
            for example_text in examples[(reason, region_name)]:
                print(f"  EXAMPLE: {example_text[:180]}")

    finally:
        session.close()


if __name__ == "__main__":
    main()
