
import re
from pathlib import Path
from dataclasses import replace

from src.models import (
    DocumentMetadata,
    QuestionRecord,
    SourceDocumentReference,
)


PAGE_PATTERN = re.compile(r"^--- Page (\d+) ---\s*$")
MAJOR_QUESTION_PATTERN = re.compile(
    r"^Question\s+(\d+)\s*$",
    re.IGNORECASE,
)
LETTER_PART_PATTERN = re.compile(
    r"^\(([a-z])\)\s*(.*)$",
    re.IGNORECASE,
)
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

MARK_SCHEME_MAJOR_ROW_PATTERN = re.compile(
    r"^(\d+)\s+(.+?)\s+(\d+)\s*$"
)

INDICATIVE_CONTENT_PATTERN = re.compile(
    r"^(?:INDICATIVE\b|OVERVIEW MIGHT INCLUDE\b|"
    r"CANDIDATES MAY REFER TO\b)",
    re.IGNORECASE,
)

LEVEL_DESCRIPTOR_PATTERN = re.compile(
    r"^(?:MARKING CRITERIA\b|MARKING CRITERIA FOR\b|"
    r"TABLE [AB],\s*(?:READING|WRITING)\b|"
    r"LEVEL\s+MARKS\s+DESCRIPTION\b)",
    re.IGNORECASE,
)

SECTION_HEADER_PATTERN = re.compile(
    r"^(?:NOTES ON THE TASK\b|"
    r"QUESTION ANSWER MARKS$)",
    re.IGNORECASE,
)


def _split_pages(text: str) -> list[tuple[int, list[str]]]:
    """Split extracted document text into numbered pages."""
    pages: list[tuple[int, list[str]]] = []
    page_number: int | None = None
    page_lines: list[str] = []

    for line in text.splitlines():
        match = PAGE_PATTERN.match(line.strip())

        if match:
            if page_number is not None:
                pages.append((page_number, page_lines))

            page_number = int(match.group(1))
            page_lines = []
        elif page_number is not None:
            page_lines.append(line)

    if page_number is not None:
        pages.append((page_number, page_lines))

    return pages


def _clean_text(lines: list[str]) -> str:
    """Clean layout artifacts without changing question wording."""
    cleaned: list[str] = []

    for line in lines:
        value = re.sub(r"\.{3,}", "", line.strip())
        value = re.sub(r"\s+", " ", value).strip()

        if not value:
            continue

        if value.startswith(("© UCLES", "© Cambridge")):
            continue

        if value in {"[Turn over]", "PUBLISHED"}:
            continue

        cleaned.append(value)

    return " ".join(cleaned).strip()


def _subject_slug(subject: str) -> str:
    """Convert a subject name into a lowercase, hyphenated identifier."""
    slug = re.sub(r"[^a-z0-9]+", "-", subject.lower()).strip("-")
    return re.sub(r"-+", "-", slug)


def _document_id(document_name: str) -> str:
    """Create a document ID from a source filename."""
    stem = Path(document_name).stem
    return _subject_slug(stem) or "source-document"


def _make_record(
    document: DocumentMetadata,
    document_id: str,
    page_number: int,
    question_number: str,
    question_text: str,
    marks: int | None,
    instructions: list[str] | None = None,
) -> QuestionRecord:
    """Create a question record with its source reference."""
    subject_slug = _subject_slug(
        document.subject or Path(document.document_name).stem
    )
    question_id = f"{subject_slug}:{question_number}"

    return QuestionRecord(
        question_id=question_id,
        question_number=question_number,
        question_text=question_text,
        source=SourceDocumentReference(
            document_id=document_id,
            page_number=page_number,
        ),
        marks=marks,
        instructions=instructions or [],
    )


def parse_question_paper_text(
    text: str,
    document: DocumentMetadata,
    source_document_id: str | None = None,
) -> list[QuestionRecord]:
    """Extract questions while keeping shared instructions separate."""
    records: list[QuestionRecord] = []
    document_id = source_document_id or _document_id(
        document.document_name
    )

    current_major: str | None = None
    parent_part: str | None = None
    parent_instruction = ""

    for page_number, lines in _split_pages(text):
        current_number: str | None = None
        current_lines: list[str] = []
        current_marks: int | None = None
        current_instructions: list[str] = []

        page_has_subquestions = False
        major_prompt_lines: list[str] = []
        major_prompt_start: int | None = None

        def flush_current() -> None:
            """Save the current question, if one has been started."""
            nonlocal current_number
            nonlocal current_lines
            nonlocal current_marks
            nonlocal current_instructions

            if current_number is not None:
                question_text = _clean_text(current_lines)

                if question_text:
                    records.append(
                        _make_record(
                            document=document,
                            document_id=document_id,
                            page_number=page_number,
                            question_number=current_number,
                            question_text=question_text,
                            marks=current_marks,
                            instructions=current_instructions,
                        )
                    )

            current_number = None
            current_lines = []
            current_marks = None
            current_instructions = []

        for line_index, line in enumerate(lines):
            stripped = line.strip()

            # Start of a new major question, e.g. Question 1.
            major_match = MAJOR_QUESTION_PATTERN.match(stripped)

            if major_match:
                flush_current()

                current_major = major_match.group(1)
                parent_part = None
                parent_instruction = ""

                major_prompt_lines = []
                major_prompt_start = line_index + 1
                page_has_subquestions = False
                continue

            # Roman-numeral subquestions must be checked before letter parts.
            roman_match = ROMAN_PART_PATTERN.match(stripped)

            if (
                roman_match
                and current_major is not None
                and parent_part is not None
            ):
                parent_number = f"{current_major}({parent_part})"

                if current_number == parent_number:
                    # The parent part contains a shared instruction, not
                    # a separate answerable question when children follow.
                    current_number = None
                    current_lines = []
                    current_marks = None
                    current_instructions = []
                else:
                    # Save the preceding Roman-numeral subquestion.
                    flush_current()

                page_has_subquestions = True

                roman_part = roman_match.group(1).lower()
                current_number = (
                    f"{current_major}({parent_part})({roman_part})"
                )

                child_text = roman_match.group(2).strip()

                # Keep only the child's own wording in question_text.
                current_lines = [child_text] if child_text else []

                # Every child inherits the parent instruction as metadata.
                current_instructions = (
                    [parent_instruction] if parent_instruction else []
                )

                major_prompt_lines = []
                major_prompt_start = None
                continue

            # Start of a lettered part, e.g. (a) or (b).
            letter_match = LETTER_PART_PATTERN.match(stripped)

            if letter_match and current_major is not None:
                flush_current()
                page_has_subquestions = True

                parent_part = letter_match.group(1).lower()
                parent_instruction = letter_match.group(2).strip()

                current_number = f"{current_major}({parent_part})"

                # Initially collect the parent instruction. If Roman
                # children follow, discard this parent-only record.
                current_lines = (
                    [parent_instruction] if parent_instruction else []
                )
                current_instructions = (
                    [parent_instruction] if parent_instruction else []
                )

                major_prompt_lines = []
                major_prompt_start = None
                continue

            # Continue collecting text for the active question.
            if current_number is not None:
                mark_matches = MARKS_PATTERN.findall(stripped)

                if mark_matches:
                    current_marks = int(mark_matches[-1])
                    stripped = MARKS_PATTERN.sub("", stripped).strip()

                if stripped and not stripped.startswith("©"):
                    current_lines.append(stripped)

            # Collect text for major questions without lettered parts.
            elif (
                major_prompt_start is not None
                and line_index >= major_prompt_start
            ):
                major_prompt_lines.append(line)

        flush_current()

        # Handle a major question with no lettered subquestions.
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
                total_marks = sum(map(int, mark_values)) or None

                records.append(
                    _make_record(
                        document=document,
                        document_id=document_id,
                        page_number=page_number,
                        question_number=current_major,
                        question_text=prompt_text,
                        marks=total_marks,
                    )
                )

    return records


# def parse_mark_scheme_text(
#     text: str,
# ) -> dict[str, dict[str, object]]:
#     """Extract mark-scheme entries keyed by question number."""
#     entries: dict[str, dict[str, object]] = {}

#     current_number: str | None = None
#     current_page = 1
#     current_lines: list[str] = []
#     current_header = ""

#     def flush_entry() -> None:
#         if current_number is None:
#             return

#         accepted_answers: list[str] = []
#         guidance_lines: list[str] = []

#         header_mark = re.search(r"\s+(\d+)\s*$", current_header)
#         marks = int(header_mark.group(1)) if header_mark else None

#         for line in current_lines:
#             bullet_match = BULLET_PATTERN.match(line)

#             if bullet_match:
#                 accepted_answers.append(bullet_match.group(1).strip())
#             elif line.strip():
#                 guidance_lines.append(line.strip())

#         entries[current_number] = {
#             "page": current_page,
#             "marks": marks,
#             "accepted_answers": accepted_answers,
#             "marking_guidance": guidance_lines,
#         }

#     for page_number, lines in _split_pages(text):
#         current_page = page_number

#         for line in lines:
#             stripped = line.strip()
#             item_match = MARK_SCHEME_ITEM_PATTERN.match(stripped)

#             if item_match:
#                 flush_entry()

#                 current_number = item_match.group(1).lower()
#                 current_header = item_match.group(2)
#                 current_lines = []
#             elif current_number is not None:
#                 current_lines.append(stripped)

#     flush_entry()
#     return entries


# def parse_mark_scheme_text(
#     text: str,
# ) -> dict[str, dict[str, object]]:
#     """Parse mark-scheme entries with question and section boundaries."""
#     entries: dict[str, dict[str, object]] = {}

#     current_number: str | None = None
#     current_page: int | None = None
#     current_header = ""
#     current_lines: list[str] = []

#     pending_major: str | None = None
#     section_type = "general"

#     def flush_entry() -> None:
#         nonlocal current_number
#         nonlocal current_page
#         nonlocal current_header
#         nonlocal current_lines
#         nonlocal section_type

#         if current_number is None:
#             return

#         accepted_answers: list[str] = []
#         marking_guidance: list[str] = []
#         indicative_content: list[str] = []
#         level_descriptors: list[str] = []

#         header_mark = re.search(r"\s+(\d+)\s*$", current_header)
#         marks = int(header_mark.group(1)) if header_mark else None

#         mode = "general"

#         for line in current_lines:
#             value = line.strip()

#             if not value:
#                 continue

#             if INDICATIVE_CONTENT_PATTERN.match(value):
#                 mode = "indicative"
#                 continue

#             if LEVEL_DESCRIPTOR_PATTERN.match(value):
#                 mode = "levels"
#                 continue

#             if SECTION_HEADER_PATTERN.match(value):
#                 # Notes on a task belong to its indicative content.
#                 if value.upper().startswith("NOTES ON THE TASK"):
#                     mode = "indicative"
#                 continue

#             if value.startswith(
#                 ("© UCLES", "© Cambridge", "0500/")
#             ) or value == "PUBLISHED":
#                 continue

#             if value in {"Question Answer Marks", "Question Answer"}:
#                 continue

#             if mode == "indicative":
#                 indicative_content.append(value)
#             elif mode == "levels":
#                 level_descriptors.append(value)
#             else:
#                 bullet_match = BULLET_PATTERN.match(value)

#                 if bullet_match:
#                     accepted_answers.append(
#                         bullet_match.group(1).strip()
#                     )
#                 else:
#                     marking_guidance.append(value)

#         entries[current_number] = {
#             "page": current_page,
#             "marks": marks,
#             "question_text": current_header,
#             "accepted_answers": accepted_answers,
#             "marking_guidance": marking_guidance,
#             "indicative_content": indicative_content,
#             "level_descriptors": level_descriptors,
#         }

#         current_number = None
#         current_page = None
#         current_header = ""
#         current_lines = []
#         section_type = "general"

#     for page_number, lines in _split_pages(text):
#         for line in lines:
#             stripped = line.strip()

#             # A major heading closes the preceding entry.
#             major_match = MAJOR_QUESTION_PATTERN.match(stripped)

#             if major_match:
#                 flush_entry()
#                 pending_major = major_match.group(1)
#                 continue

#             # Ordinary entries, e.g. 1(a), 2(b)(i), 2(d).
#             item_match = MARK_SCHEME_ITEM_PATTERN.match(stripped)

#             if item_match:
#                 flush_entry()

#                 current_number = item_match.group(1).lower()
#                 current_header = item_match.group(2)
#                 current_page = page_number
#                 current_lines = []
#                 pending_major = None
#                 continue

#             # Major task rows, e.g.:
#             # 3 You are Mike. ... 25
#             major_row = MARK_SCHEME_MAJOR_ROW_PATTERN.match(stripped)

#             if (
#                 major_row
#                 and pending_major is not None
#                 and major_row.group(1) == pending_major
#             ):
#                 flush_entry()

#                 current_number = pending_major
#                 current_header = (
#                     f"{major_row.group(2)} {major_row.group(3)}"
#                 )
#                 current_page = page_number
#                 current_lines = []
#                 pending_major = None
#                 continue

#             # Recognise section changes without closing the question.
#             if current_number is not None:
#                 if INDICATIVE_CONTENT_PATTERN.match(stripped):
#                     section_type = "indicative"
#                 elif LEVEL_DESCRIPTOR_PATTERN.match(stripped):
#                     section_type = "levels"

#                 current_lines.append(stripped)

#     flush_entry()
#     return entries


def parse_mark_scheme_text(
    text: str,
) -> dict[str, dict[str, object]]:
    """Parse mark-scheme entries without crossing question boundaries."""
    entries: dict[str, dict[str, object]] = {}

    current_number: str | None = None
    current_page: int | None = None
    current_header = ""
    current_lines: list[str] = []

    pending_major: str | None = None

    def flush_entry() -> None:
        nonlocal current_number
        nonlocal current_page
        nonlocal current_header
        nonlocal current_lines

        if current_number is None:
            return

        accepted_answers: list[str] = []
        marking_guidance: list[str] = []
        indicative_content: list[str] = []
        level_descriptors: list[str] = []

        header_mark = re.search(r"\s+(\d+)\s*$", current_header)
        marks = int(header_mark.group(1)) if header_mark else None

        mode = "general"

        for line in current_lines:
            value = line.strip()

            if not value:
                continue

            # Switch classification when a section heading appears.
            if INDICATIVE_CONTENT_PATTERN.match(value):
                mode = "indicative"
                continue

            if LEVEL_DESCRIPTOR_PATTERN.match(value):
                mode = "levels"
                continue

            if SECTION_HEADER_PATTERN.match(value):
                if value.upper().startswith("NOTES ON THE TASK"):
                    mode = "indicative"
                continue

            # Ignore recurring PDF headers and footers.
            if (
                value.startswith(
                    ("© UCLES", "© Cambridge", "0500/")
                )
                or value == "PUBLISHED"
                or value in {
                    "Question Answer Marks",
                    "Question Answer",
                }
            ):
                continue

            if mode == "indicative":
                indicative_content.append(value)
            elif mode == "levels":
                level_descriptors.append(value)
            else:
                bullet_match = BULLET_PATTERN.match(value)

                if bullet_match:
                    answer_text = bullet_match.group(1).strip()
                    accepted_answers.extend(
                        option.strip()
                        for option in answer_text.split("/")
                        if option.strip()
                    )
                else:
                    marking_guidance.append(value)

        entries[current_number] = {
            "page": current_page,
            "marks": marks,
            "question_text": current_header,
            "accepted_answers": accepted_answers,
            "marking_guidance": marking_guidance,
            "indicative_content": indicative_content,
            "level_descriptors": level_descriptors,
        }

        current_number = None
        current_page = None
        current_header = ""
        current_lines = []

    for page_number, lines in _split_pages(text):
        for line in lines:
            stripped = line.strip()

            if not stripped:
                continue

            # A major heading closes the previous entry immediately.
            major_match = MAJOR_QUESTION_PATTERN.match(stripped)

            if major_match:
                flush_entry()
                pending_major = major_match.group(1)
                continue

            # Major-question table row, e.g.:
            # 3 You are Mike. ... 25
            major_row = MARK_SCHEME_MAJOR_ROW_PATTERN.match(stripped)

            if (
                major_row is not None
                and pending_major is not None
                and major_row.group(1) == pending_major
            ):
                flush_entry()

                current_number = pending_major
                current_header = (
                    f"{major_row.group(2)} {major_row.group(3)}"
                )
                current_page = page_number
                current_lines = []
                pending_major = None
                continue

            # Subquestions such as 1(a), 2(b)(i), and 2(d).
            item_match = MARK_SCHEME_ITEM_PATTERN.match(stripped)

            if item_match:
                flush_entry()

                current_number = item_match.group(1).lower()
                current_header = item_match.group(2)
                current_page = page_number
                current_lines = []
                pending_major = None
                continue

            if current_number is not None:
                current_lines.append(stripped)

    flush_entry()
    return entries




# def attach_mark_scheme(
#     records: list[QuestionRecord],
#     mark_scheme: dict[str, dict[str, object]],
#     mark_scheme_document: DocumentMetadata,
#     mark_scheme_document_id: str | None = None,
# ) -> list[QuestionRecord]:
#     """Attach matching answers and marking guidance to each question."""
#     document_id = (
#         mark_scheme_document_id
#         or _document_id(mark_scheme_document.document_name)
#     )
#     enriched_records: list[QuestionRecord] = []

#     for record in records:
#         entry = mark_scheme.get(record.question_number.lower())

#         if entry is None:
#             enriched_records.append(
#                 replace(
#                     record,
#                     review_required=True,
#                     review_issues=[
#                         *record.review_issues,
#                         "No matching mark-scheme entry was extracted.",
#                     ],
#                 )
#             )
#             continue

#         page_value = entry.get("page")
#         answers_value = entry.get("accepted_answers", [])
#         guidance_value = entry.get("marking_guidance", [])
#         marks_value = entry.get("marks")

#         mark_scheme_source = (
#             SourceDocumentReference(
#                 document_id=document_id,
#                 page_number=int(page_value),
#             )
#             if page_value is not None
#             else None
#         )

#         accepted_answers = (
#             [str(value) for value in answers_value]
#             if isinstance(answers_value, list)
#             else []
#         )
#         marking_guidance = (
#             [str(value) for value in guidance_value]
#             if isinstance(guidance_value, list)
#             else []
#         )

#         scheme_marks = (
#             float(marks_value)
#             if isinstance(marks_value, (int, float))
#             else None
#         )

#         enriched_records.append(
#             replace(
#                 record,
#                 marks=(
#                     record.marks
#                     if record.marks is not None
#                     else scheme_marks
#                 ),
#                 accepted_answers=accepted_answers,
#                 marking_guidance=marking_guidance,
#                 mark_scheme_source=mark_scheme_source,
#             )
#         )

#     return enriched_records


def attach_mark_scheme(
    records: list[QuestionRecord],
    mark_scheme: dict[str, dict[str, object]],
    mark_scheme_document: DocumentMetadata,
    mark_scheme_document_id: str | None = None,
) -> list[QuestionRecord]:
    """Attach matching mark-scheme content to each question."""
    document_id = (
        mark_scheme_document_id
        or _document_id(mark_scheme_document.document_name)
    )
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

        page_value = entry.get("page")
        answers_value = entry.get("accepted_answers", [])
        indicative_value = entry.get("indicative_content", [])
        guidance_value = entry.get("marking_guidance", [])
        descriptors_value = entry.get("level_descriptors", [])
        marks_value = entry.get("marks")

        mark_scheme_source = (
            SourceDocumentReference(
                document_id=document_id,
                page_number=int(page_value),
            )
            if isinstance(page_value, (int, float))
            else None
        )

        accepted_answers = (
            [str(value) for value in answers_value]
            if isinstance(answers_value, list)
            else []
        )
        indicative_content = (
            [str(value) for value in indicative_value]
            if isinstance(indicative_value, list)
            else []
        )
        marking_guidance = (
            [str(value) for value in guidance_value]
            if isinstance(guidance_value, list)
            else []
        )
        level_descriptors = (
            [str(value) for value in descriptors_value]
            if isinstance(descriptors_value, list)
            else []
        )

        scheme_marks = (
            float(marks_value)
            if isinstance(marks_value, (int, float))
            else None
        )

        enriched_records.append(
            replace(
                record,
                marks=(
                    record.marks
                    if record.marks is not None
                    else scheme_marks
                ),
                accepted_answers=accepted_answers,
                indicative_content=indicative_content,
                marking_guidance=marking_guidance,
                level_descriptors=level_descriptors,
                mark_scheme_source=mark_scheme_source,
            )
        )

    return enriched_records