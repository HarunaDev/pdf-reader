
import json
from pathlib import Path

from src.models import QuestionRecord
from src.validator import QuestionReview


def write_questions_json(
    valid_records: list[QuestionRecord],
    review_records: list[QuestionReview],
    output_path: Path,
) -> None:
    """Write validated questions and review records to JSON."""

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    payload = {
        "valid_records": [
            record.to_dict()
            for record in valid_records
        ],
        "review_records": [
            {
                "record": review.record.to_dict(),
                "issues": review.issues,
            }
            for review in review_records
        ],
        "summary": {
            "valid_count": len(valid_records),
            "review_count": len(review_records),
            "total_count": (
                len(valid_records) + len(review_records)
            ),
        },
    }

    with output_path.open("w", encoding="utf-8") as json_file:
        json.dump(
            payload,
            json_file,
            indent=2,
            ensure_ascii=False,
            allow_nan=False,
        )

    print(f"JSON saved to: {output_path}")
    print(f"Valid records: {len(valid_records)}")
    print(f"Records requiring review: {len(review_records)}")
