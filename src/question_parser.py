import re
from pathlib import Path
from dataclasses import replace

from src.models import QuestionRecord, SourceMetadata, DocumentMetadata


PAGE_PATTERN = re.compile(r"^--- Page (\d+) ---\s*$")
MAJOR_QUESTION_PATTERN = re.compile(r"^Question (\d+)\s*$", re.IGNORECASE)
LETTER_PART_PATTERN = re.compile(r"^\(([a-z])\)\s*(.*)$")
ROMAN_PART_PATTERN = re.compile(
    r"^\((i{1,3}|iv|v|vi{0,3}|ix|x)\)\s*(.*)$",
    re.IGNORECASE,
)
MARKS_PATTERN = re.compile(r"\[(\d+)\]")
MARK_SCHEME_ITEM_PATTERN = re.compile(
    r"^(\d+\([a-z]\)(?:\([ivx]+\))?)\s+(.+)$",
    re.IGNORECASE,
)
BULLET_PATTERN = re.compile(r"^\s*[•▪◦]\s*(.+)$")


def _split_pages(text: str) -> list[tuple[int, list[str]]]:
    """Split extracted document text into numbered pages."""
    pages: list[tuple[int, list[str]]] = []
    page_number: int | None = None
    page_lines: list[str] = []

    for line in text.splitlines():
        page_match = PAGE_PATTERN.match(line.strip())

        if page_match:
            if page_number is not None:
                pages.append((page_number, page_lines))

            page_number = int(page_match.group(1))
            page_lines = []
        elif page_number is not None:
            page_lines.append(line)

    if page_number is not None:
        pages.append((page_number, page_lines))

    return pages


def _clean_text(lines: list[str]) -> str:
    """Clean layout artifacts without changing the wording of a question."""
    cleaned_lines: list[str] = []

    for line in lines:
        value = line.strip()
        value = re.sub(r"\.{3,}", "", value)
        value = re.sub(r"\s+", " ", value)

        if not value:
            continue

        if value.startswith("© UCLES") or value.startswith("© Cambridge"):
            continue

        if value in {"[Turn over]", "PUBLISHED"}:
            continue

        cleaned_lines.append(value)

    return " ".join(cleaned_lines).strip()

def _subject_slug(subject: str) -> str:
    """Convert a subject name into a lowercase, hyphenated identifier."""
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", subject.lower())).strip("-")

# def _make_record(
#     document_name: str,
#     page_number: int,
#     question_number: str,
#     question_text: str,
#     marks: int | None,
# ) -> QuestionRecord:
#     question_id = f"{document_name}:{question_number}"

#     source = SourceMetadata(
#         document_name=document_name,
#         page_number=page_number,
#         question_id=question_id,
#     )

#     return QuestionRecord(
#         question_id=question_id,
#         question_number=question_number,
#         question_text=question_text,
#         marks=marks,
#         source=source,
#     )

def _make_record(
    document: DocumentMetadata,
    page_number: int,
    question_number: str,
    question_text: str,
    marks: int | None,
) -> QuestionRecord:
    subject_slug = _subject_slug(
        document.subject or document.document_name.rsplit(".", 1)[0]
    )
    question_id = f"{subject_slug}:{question_number}"

    source = SourceMetadata(
        document_name=document.document_name,
        page_number=page_number,
        question_id=question_id,
    )

    return QuestionRecord(
        question_id=question_id,
        question_number=question_number,
        question_text=question_text,
        document=document,
        source=source,
        marks=marks,
    )

def parse_question_paper_text(
    text: str,
    document: DocumentMetadata,
) -> list[QuestionRecord]:
    """Extract numbered questions and nested subquestions."""
    records: list[QuestionRecord] = []
    current_major: str | None = None
    parent_part: str | None = None

    for page_number, lines in _split_pages(text):
        current_number: str | None = None
        current_lines: list[str] = []
        current_marks: int | None = None

        page_has_subquestions = False
        major_prompt_lines: list[str] = []
        major_prompt_start: int | None = None

        def flush_current() -> None:
            nonlocal current_number, current_lines, current_marks

            if current_number is not None:
                question_text = _clean_text(current_lines)

                if question_text:
                    records.append(
                        _make_record(
                            document=document,
                            page_number=page_number,
                            question_number=current_number,
                            question_text=question_text,
                            marks=current_marks,
                        )
                    )

            current_number = None
            current_lines = []
            current_marks = None

        for line_index, line in enumerate(lines):
            stripped = line.strip()

            major_match = MAJOR_QUESTION_PATTERN.match(stripped)

            if major_match:
                flush_current()
                current_major = major_match.group(1)
                parent_part = None
                major_prompt_lines = []
                major_prompt_start = line_index + 1
                page_has_subquestions = False
                continue

            roman_match = ROMAN_PART_PATTERN.match(stripped)
            letter_match = LETTER_PART_PATTERN.match(stripped)

            # Check for a nested Roman-numeral part BEFORE
            # interpreting the line as a lettered part.
            if (
                roman_match
                and current_major is not None
                and parent_part is not None
            ):
                parent_number = f"{current_major}({parent_part})"
                parent_prompt = ""

                # The current record may be the parent instruction,
                # rather than a question in its own right.
                if (
                    current_number == parent_number
                    and current_marks is None
                ):
                    parent_prompt = _clean_text(current_lines)

                    # Save the parent instruction as context instead
                    # of emitting a separate parent question record.
                    current_number = None
                    current_lines = []
                    current_marks = None
                else:
                    flush_current()

                page_has_subquestions = True
                roman_part = roman_match.group(1).lower()
                current_number = (
                    f"{current_major}({parent_part})({roman_part})"
                )

                current_lines = []

                if parent_prompt:
                    current_lines.append(parent_prompt)

                if roman_match.group(2).strip():
                    current_lines.append(roman_match.group(2).strip())

                major_prompt_lines = []
                major_prompt_start = None
                continue

            if letter_match and current_major is not None:
                flush_current()

                page_has_subquestions = True
                parent_part = letter_match.group(1).lower()
                current_number = f"{current_major}({parent_part})"
                current_lines = []

                if letter_match.group(2).strip():
                    current_lines.append(letter_match.group(2).strip())

                major_prompt_lines = []
                major_prompt_start = None
                continue

            if current_number is not None:
                mark_matches = MARKS_PATTERN.findall(stripped)

                if mark_matches:
                    current_marks = int(mark_matches[-1])
                    stripped = MARKS_PATTERN.sub("", stripped).strip()

                if stripped and not stripped.startswith("©"):
                    current_lines.append(stripped)

            elif (
                major_prompt_start is not None
                and line_index >= major_prompt_start
            ):
                major_prompt_lines.append(line)

        flush_current()

        # Preserve extended-response questions without lettered parts.
        if (
            current_major is not None
            and not page_has_subquestions
            and major_prompt_start is not None
            and major_prompt_lines
        ):
            prompt_text = _clean_text(major_prompt_lines)

            if prompt_text:
                mark_values = re.findall(
                    r"Up to (\d+) marks? are available",
                    prompt_text,
                    re.IGNORECASE,
                )
                total_marks = sum(
                    int(value) for value in mark_values
                ) or None

                records.append(
                    _make_record(
                        document=document,
                        page_number=page_number,
                        question_number=current_major,
                        question_text=prompt_text,
                        marks=total_marks,
                    )
                )

    return records


def parse_mark_scheme_text(
    text: str,
) -> dict[str, dict[str, object]]:
    """Extract point-based mark-scheme entries keyed by question number."""
    entries: dict[str, dict[str, object]] = {}
    current_number: str | None = None
    current_page = 1
    current_lines: list[str] = []
    current_header = ""

    def flush_entry() -> None:
        if current_number is None:
            return

        accepted_answers: list[str] = []
        guidance_lines: list[str] = []
        marks: int | None = None

        header_mark = re.search(r"\s+(\d+)\s*$", current_header)
        if header_mark:
            marks = int(header_mark.group(1))

        for line in current_lines:
            bullet_match = BULLET_PATTERN.match(line)

            if bullet_match:
                accepted_answers.append(bullet_match.group(1).strip())
            elif line.strip():
                guidance_lines.append(line.strip())

        entries[current_number] = {
            "page": current_page,
            "marks": marks,
            "accepted_answers": accepted_answers,
            "marking_guidance": guidance_lines,
        }

    for page_number, lines in _split_pages(text):
        current_page = page_number

        for line in lines:
            stripped = line.strip()
            item_match = MARK_SCHEME_ITEM_PATTERN.match(stripped)

            if item_match:
                flush_entry()
                current_number = item_match.group(1).lower()
                current_header = item_match.group(2)
                current_lines = []
            elif current_number is not None:
                current_lines.append(stripped)

    flush_entry()
    return entries



def attach_mark_scheme(
    records: list[QuestionRecord],
    mark_scheme: dict[str, dict[str, object]],
    mark_scheme_document: DocumentMetadata,
) -> list[QuestionRecord]:
    """Attach matching mark-scheme content to extracted questions."""
    enriched_records: list[QuestionRecord] = []

    for record in records:
        entry = mark_scheme.get(record.question_number.lower())

        if entry is None:
            enriched_records.append(
                replace(
                    record,
                    review_required=True,
                    review_issues=[
                        *record.review_issues,
                        "No matching mark-scheme entry was extracted.",
                    ],
                )
            )
            continue

        mark_scheme_source = SourceMetadata(
            document_name=mark_scheme_document.document_name,
            page_number=int(entry["page"]),
            question_id=record.question_id,
        )

        accepted_answers = list(entry["accepted_answers"])
        marking_guidance = list(entry["marking_guidance"])
        entry_marks = entry["marks"]

        enriched_records.append(
            replace(
                record,
                marks=(
                    record.marks
                    if record.marks is not None
                    else entry_marks
                ),
                accepted_answers=accepted_answers,
                marking_guidance=marking_guidance,
                mark_scheme_source=mark_scheme_source,
            )
        )

    return enriched_records
