from dataclasses import dataclass

from src.models import QuestionRecord


@dataclass(frozen=True, slots=True)
class QuestionReview:
    record: QuestionRecord
    issues: list[str]


def validate_records(
    records: list[QuestionRecord],
) -> tuple[list[QuestionRecord], list[QuestionReview]]:
    """Separate complete question records from records requiring review."""

    valid_records: list[QuestionRecord] = []
    review_records: list[QuestionReview] = []

    for record in records:
        issues = list(record.review_issues)

        if not record.question_id.strip():
            issues.append("Question ID is missing.")

        if not record.question_number.strip():
            issues.append("Question number is missing.")

        if not record.question_text.strip():
            issues.append("Question text is missing.")

        if record.source is None:
            issues.append("Question source metadata is missing.")
        else:
            if not record.source.document_name.strip():
                issues.append("Source document name is missing.")

            if record.source.page_number < 1:
                issues.append("Source page number must be positive.")

            if not record.source.question_id.strip():
                issues.append("Source question ID is missing.")

        if record.marks is not None and record.marks < 0:
            issues.append("Marks cannot be negative.")

        # Remove duplicate issue messages.
        issues = list(dict.fromkeys(issues))

        if issues:
            review_records.append(
                QuestionReview(record=record, issues=issues)
            )
        else:
            valid_records.append(record)

    return valid_records, review_records