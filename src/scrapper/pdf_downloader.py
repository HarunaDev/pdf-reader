
import hashlib
import json
import os
import tempfile
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import pdfplumber
import requests

REQUEST_TIMEOUT = 30
MAX_ATTEMPTS = 3
CHUNK_SIZE = 64 * 1024

USER_AGENT = "pdf-scanner/1.0 (educational resource downloader)"


@dataclass(frozen=True, slots=True)
class DownloadResult:
    url: str
    local_path: str | None
    status: str
    attempts: int
    file_size: int | None
    error: str | None = None


def validate_pdf(file_path: Path) -> tuple[bool, str | None]:
    """Check the PDF signature and confirm pdfplumber can open the file."""
    try:
        with file_path.open("rb") as file:
            signature = file.read(5)

        if signature != b"%PDF-":
            return False, "Downloaded content does not have a PDF signature"

        with pdfplumber.open(file_path) as pdf:
            if not pdf.pages:
                return False, "PDF contains no pages"

        return True, None

    except Exception as exc:
        return False, f"PDF validation failed: {exc}"


def _temporary_path(destination: Path) -> Path:
    """Create a temporary file in the destination directory."""
    with tempfile.NamedTemporaryFile(
        prefix=".download-",
        suffix=".tmp",
        dir=destination.parent,
        delete=False,
    ) as temporary_file:
        return Path(temporary_file.name)


def download_pdf(
    url: str,
    destination: Path,
    session: requests.Session,
) -> DownloadResult:
    """Download one PDF safely, retry transient failures, and validate it."""
    if urlparse(url).scheme != "https":
        return DownloadResult(
            url=url,
            local_path=None,
            status="failed",
            attempts=0,
            file_size=None,
            error="Only HTTPS download URLs are allowed",
        )

    destination.parent.mkdir(parents=True, exist_ok=True)

    # A previous successful download can be reused after validation.
    if destination.is_file():
        is_valid, validation_error = validate_pdf(destination)

        if is_valid:
            return DownloadResult(
                url=url,
                local_path=str(destination),
                status="skipped_existing",
                attempts=0,
                file_size=destination.stat().st_size,
            )

        print(
            f"Existing file is invalid and will be replaced: "
            f"{destination} ({validation_error})"
        )

    last_error = "Download did not complete"

    for attempt in range(1, MAX_ATTEMPTS + 1):
        temporary_path: Path | None = None

        try:
            with session.get(
                url,
                stream=True,
                timeout=REQUEST_TIMEOUT,
                headers={"User-Agent": USER_AGENT},
            ) as response:
                if response.status_code == 429 or response.status_code >= 500:
                    last_error = f"Temporary HTTP error: {response.status_code}"

                    if attempt < MAX_ATTEMPTS:
                        time.sleep(2 ** (attempt - 1))
                        continue

                    break

                response.raise_for_status()

                temporary_path = _temporary_path(destination)

                with temporary_path.open("wb") as file:
                    for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
                        if chunk:
                            file.write(chunk)

            is_valid, validation_error = validate_pdf(temporary_path)

            if not is_valid:
                last_error = validation_error or "Invalid PDF"

                if attempt < MAX_ATTEMPTS:
                    temporary_path.unlink(missing_ok=True)
                    time.sleep(2 ** (attempt - 1))
                    continue

                break

            file_size = temporary_path.stat().st_size

            # Publish the file only after it passes validation.
            os.replace(temporary_path, destination)
            temporary_path = None

            return DownloadResult(
                url=url,
                local_path=str(destination),
                status="downloaded",
                attempts=attempt,
                file_size=file_size,
            )

        except requests.HTTPError as exc:
            last_error = str(exc)
            status_code = (
                exc.response.status_code
                if exc.response is not None
                else None
            )

            # Permanent client errors, such as 404, should not be retried.
            if status_code is not None and 400 <= status_code < 500:
                break

        except (requests.RequestException, OSError) as exc:
            last_error = str(exc)

        finally:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)

        if attempt < MAX_ATTEMPTS:
            time.sleep(2 ** (attempt - 1))

    return DownloadResult(
        url=url,
        local_path=None,
        status="failed",
        attempts=attempt,
        file_size=None,
        error=last_error,
    )


def _resource_destination(
    root: Path,
    syllabus_code: str,
    year: int | None,
    session_name: str | None,
    paper: str | None,
    resource_type: str,
    url: str,
) -> Path:
    """Create a stable, collision-resistant destination for a resource."""
    year_directory = str(year) if year is not None else "unknown-year"
    session_directory = (
        (session_name or "unknown-session").casefold().replace("/", "-")
    )
    paper_directory = f"paper-{paper}" if paper else "unknown-paper"

    url_hash = hashlib.sha256(url.encode("utf-8")).hexdigest()[:12]

    return (
        root
        / syllabus_code
        / year_directory
        / session_directory
        / paper_directory
        / f"{resource_type}-{url_hash}.pdf"
    )


def download_manifest(
    manifest_path: Path,
    output_directory: Path,
    report_path: Path,
) -> list[DownloadResult]:
    """
    Download resources from the grouped ExamEntry manifest.

    Expected fields include question_paper, mark_scheme, and
    reading_passage, each containing a title and URL or null.
    """
    with manifest_path.open("r", encoding="utf-8") as file:
        entries: list[dict[str, Any]] = json.load(file)

    results: list[DownloadResult] = []
    url_results: dict[str, DownloadResult] = {}

    with requests.Session() as session:
        for entry in entries:
            syllabus_code = str(entry["syllabus_code"])
            year = entry.get("year")
            session_name = entry.get("session")
            paper = entry.get("paper")

            resource_fields = (
                ("question_paper", "question_paper"),
                ("mark_scheme", "mark_scheme"),
                ("reading_passage", "reading_passage"),
            )

            for field_name, resource_type in resource_fields:
                resource = entry.get(field_name)

                if not resource:
                    continue

                url = resource.get("url")
                if not url:
                    continue

                # Reuse the outcome for a URL that already appeared in
                # this run, avoiding duplicate HTTP requests.
                if url in url_results:
                    previous = url_results[url]
                    result = DownloadResult(
                        url=previous.url,
                        local_path=previous.local_path,
                        status=(
                            "reused_duplicate_url"
                            if previous.local_path
                            else "failed"
                        ),
                        attempts=0,
                        file_size=previous.file_size,
                        error=previous.error,
                    )
                    results.append(result)
                    continue

                destination = _resource_destination(
                    root=output_directory,
                    syllabus_code=syllabus_code,
                    year=year,
                    session_name=session_name,
                    paper=paper,
                    resource_type=resource_type,
                    url=url,
                )

                print(f"Downloading {resource_type}: {url}")

                result = download_pdf(
                    url=url,
                    destination=destination,
                    session=session,
                )

                url_results[url] = result
                results.append(result)

                print(f"  Status: {result.status}")

                if result.error:
                    print(f"  Error: {result.error}")

    report_path.parent.mkdir(parents=True, exist_ok=True)

    with report_path.open("w", encoding="utf-8") as file:
        json.dump(
            [asdict(result) for result in results],
            file,
            indent=2,
            ensure_ascii=False,
        )
        file.write("\n")

    return results
