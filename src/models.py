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
        """Convert the record into a JSON-serializable dictionary."""
        return asdict(self)

@dataclass(frozen=True, slots=True)
class ExtractionOutput:
    """Complete, document-level result produced by the extraction pipeline."""

    paper: ExaminationPaper
    source_documents: list[SourceDocument]
    valid_records: list[QuestionRecord]
    review_records: list[QuestionRecord]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)
