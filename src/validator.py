from dataclasses import replace

from src.models import QuestionRecord

# def validate_records(
#     records: list[QuestionRecord],
#     source_document_ids: set[str] | None = None,
# ) -> tuple[list[QuestionRecord], list[QuestionRecord]]:
#     """Separate valid questions from records that need manual review."""
#     valid_records: list[QuestionRecord] = []
#     review_records: list[QuestionRecord] = []

#     known_document_ids = source_document_ids or set()

#     for record in records:
#         issues = list(record.review_issues)

#         if not record.question_number.strip():
#             issues.append("Question number is missing.")

#         if not record.question_text.strip():
#             issues.append("Question text is missing.")

#         if record.source.page_number < 1:
#             issues.append("Question source page number must be at least 1.")

#         if (
#             known_document_ids
#             and record.source.document_id not in known_document_ids
#         ):
#             issues.append(
#                 "Question references an unknown source document."
#             )

#         if record.marks is not None and record.marks < 0:
#             issues.append("Question marks cannot be negative.")

#         if record.mark_scheme_source is not None:
#             if record.mark_scheme_source.page_number < 1:
#                 issues.append(
#                     "Mark-scheme source page number must be at least 1."
#                 )

#             if (
#                 known_document_ids
#                 and record.mark_scheme_source.document_id
#                 not in known_document_ids
#             ):
#                 issues.append(
#                     "Mark-scheme reference points to an unknown document."
#                 )

#         # Remove duplicate validation messages while preserving order.
#         unique_issues = list(dict.fromkeys(issues))
#         needs_review = record.review_required or bool(unique_issues)

#         validated_record = replace(
#             record,
#             review_required=needs_review,
#             review_issues=unique_issues,
#         )

#         if needs_review:
#             review_records.append(validated_record)
#         else:
#             valid_records.append(validated_record)

#     return valid_records, review_records


def validate_records(
    records: list[QuestionRecord],
    source_document_ids: set[str],
) -> tuple[list[QuestionRecord], list[QuestionRecord]]:
    """Separate records that pass structural checks from those needing review."""
    valid_records: list[QuestionRecord] = []
    review_records: list[QuestionRecord] = []

    for record in records:
        issues = list(record.review_issues)

        if not record.question_number.strip():
            issues.append("Question number is missing.")

        if not record.question_text.strip():
            issues.append("Question text is missing.")

        if record.source.page_number < 1:
            issues.append("Question source page number must be at least 1.")

        if record.source.document_id not in source_document_ids:
            issues.append("Question references an unknown source document.")

        if record.marks is not None and record.marks < 0:
            issues.append("Question marks cannot be negative.")

        if record.mark_scheme_source is not None:
            if record.mark_scheme_source.page_number < 1:
                issues.append(
                    "Mark-scheme source page number must be at least 1."
                )

            if (
                record.mark_scheme_source.document_id
                not in source_document_ids
            ):
                issues.append(
                    "Mark-scheme reference points to an unknown document."
                )

        unique_issues = list(dict.fromkeys(issues))

        validated_record = replace(
            record,
            review_required=bool(unique_issues),
            review_issues=unique_issues,
        )

        if validated_record.review_required:
            review_records.append(validated_record)
        else:
            valid_records.append(validated_record)

    return valid_records, review_records