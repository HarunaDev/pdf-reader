
import re


# Lines containing only answer-space placeholders.
PLACEHOLDER_LINE = re.compile(
    r"^\s*[•·▪\-]?\s*[.\u2026…·\s]+\s*$"
)

# Runs of dots used as answer-writing spaces.
DOT_LEADERS = re.compile(r"\.{3,}|…{2,}|…")

# Common page footer and copyright text.
COPYRIGHT_FOOTER = re.compile(
    r"^\s*©\s*(?:UCLES|Cambridge)\b.*$",
    re.IGNORECASE,
)

# A page number by itself.
PAGE_NUMBER = re.compile(r"^\s*\d{1,3}\s*$")


def clean_extracted_text(text: str) -> str:
    """Remove PDF answer-space placeholders and page furniture."""

    cleaned_lines: list[str] = []

    for raw_line in text.splitlines():
        line = raw_line.strip()

        if not line:
            continue

        if PLACEHOLDER_LINE.fullmatch(line):
            continue

        if COPYRIGHT_FOOTER.match(line):
            continue

        # Remove dotted answer spaces, including those after a prompt.
        line = DOT_LEADERS.sub("", line)

        # Remove empty bullet placeholders left after cleaning.
        line = re.sub(r"^\s*[•·▪]\s*$", "", line).strip()

        if not line:
            continue

        if PAGE_NUMBER.fullmatch(line):
            continue

        cleaned_lines.append(line)

    # Keep line boundaries because the question parser needs them.
    return "\n".join(cleaned_lines)
