from dataclasses import asdict, dataclass, field
from typing import Literal

DocumentType = Literal["question_paper", "mark_scheme", "unknown"]

PaperType = Literal[
    "Reading",
    "Writing",
    "Listening",
    "Speaking",
    "Reading and Writing",
    "Other",
    "Unknown",
]

QuestionType = Literal[
    "short_answer",
    "multiple_choice",
    "extended_response",
    "summary",
    "language_analysis",
    "unknown",
]


@dataclass(frozen=True, slots=True)
class DocumentMetadata:
    """Identifies where an extracted question originated."""

    document_name: str
    document_type: DocumentType = "unknown"
    subject: str | None = None
    subject_code: str | None = None
    paper_code: str | None = None
    paper_number: int | None = None
    paper_title: str | None = None
    paper_type: PaperType = "Unknown"
    examination_session: str | None = None
    examination_year: int | None = None
    qualification: str | None = None

@dataclass(frozen=True, slots=True)
class ExaminationPaper:
    """Shared metadata describing an examination paper."""

    paper_id: str
    subject: str | None = None
    subject_code: str | None = None
    paper_code: str | None = None
    paper_number: int | None = None
    paper_title: str | None = None
    paper_type: PaperType = "Unknown"
    examination_session: str | None = None
    examination_year: int | None = None
    qualification: str | None = None

@dataclass(frozen=True, slots=True)
class SourceDocument:
    """A physical PDF associated with an examination paper."""

    document_id: str
    document_name: str
    document_type: DocumentType

@dataclass(frozen=True, slots=True)
class SourceDocumentReference:
    """A reference to a page in a source PDF."""

    document_id: str
    page_number: int

# @dataclass(frozen=True, slots=True)
# class SourceMetadata:
#     """Location of extracted content in its original document."""
#     document_name: str
#     page_number: int
#     question_id: str

@dataclass(frozen=True, slots=True)
class QuestionRecord:
    """A structured examination question and it's marking information."""

    question_id: str
    question_number: str
    question_text: str
    # document: DocumentMetadata
    source: SourceDocumentReference

    parent_question_id: str | None = None

    # document: DocumentMetadata
    # source: SourceMetadata

    question_type: QuestionType = "unknown"
    marks: float | None = None
    instructions: list[str] = field(default_factory=list)
    # source: SourceMetadata | None = None

    # Populated when a matching mark scheme is available.
    accepted_answers: list[str] = field(default_factory=list)
    indicative_content: list[str] = field(default_factory=list)
    marking_guidance: list[str] = field(default_factory=list)
    level_descriptors: list[str] = field(default_factory=list)
    mark_scheme_source: SourceDocumentReference | None = None

    # Set when extraction is uncertain or incomplete.
    review_required: bool = False
    review_issues: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        """Convert the record into a JSON-serializable record based on the agreed import contract."""
        return {
            "question_id": self.question_id,
            "question_number": self.question_number,
            "parent_question_id": self.parent_question_id,
            "question_text": self.question_text,
            "question_type": self.question_type,
            "marks": self.marks,
            "instructions": self.instructions,
            "answers": {
                "accepted_answers": self.accepted_answers,
                "indicative_content": self.indicative_content,
                "marking_guidance": self.marking_guidance,
                "level_descriptors": self.level_descriptors,
            },
            "sources": {
                "question": asdict(self.source),
                "mark_scheme": (
                    asdict(self.mark_scheme_source)
                    if self.mark_scheme_source is not None
                    else None
                ),
            },
            "review": {
                "status": (
                    "needs_review"
                    if self.review_required
                    else "ready_for_import"
                ),
                "issues": self.review_issues,
            },
        }

# @dataclass(frozen=True, slots=True)
# class ExtractionOutput:
#     """Complete, document-level result produced by the extraction pipeline."""

#     paper: ExaminationPaper
#     source_documents: list[SourceDocument]
#     valid_records: list[QuestionRecord]
#     review_records: list[QuestionRecord]

#     def to_dict(self) -> dict[str, object]:
#         return asdict(self)

@dataclass(frozen=True, slots=True)
class ExtractionOutput:
    """Versioned document-level result of the extraction pipeline."""

    paper: ExaminationPaper
    source_documents: list[SourceDocument]
    records: list[QuestionRecord]
    schema_version: str = "1.0.0"

    def to_dict(self) -> dict[str, object]:
        """Convert the result into the public import contract."""
        return {
            "schema_version": self.schema_version,
            "paper": asdict(self.paper),
            "source_documents": [
                asdict(document)
                for document in self.source_documents
            ],
            "records": [
                record.to_dict()
                for record in self.records
            ],
        }