
# from pathlib import Path

# import pdfplumber

# BASE_DIR = Path(__file__).resolve().parents[1]
# PDF_PATH = (
#     BASE_DIR
#     / "data"
#     / "exam-question.pdf"
# )


# def main() -> None:
#     if not PDF_PATH.is_file():
#         raise FileNotFoundError(f"PDF not found: {PDF_PATH}")
    
#     with pdfplumber.open(PDF_PATH) as pdf:
#         page_indices = (1, 2, 5, 9)

#         for page_index in page_indices:
#             if page_index >= len(pdf.pages):
#                 continue

#             page = pdf.pages[page_index]

#             print(f"\n{'=' * 70}")
#             print(f"PAGE {page_index + 1}")
#             print("=" * 70)

#             # print("\n--- EXTRACTED TEXT ---")
#             # print(page.extract_text() or "[No text extracted]")

#             # print("\n--- EXTRACTED TABLES ---")
#             # for table_index, table in enumerate(
#             #     page.extract_tables() or [],
#             #     start=1,
#             # ):
#             #     print(f"\nTable {table_index}:")
#             #     for row in table:
#             #         print(repr(row))

#             strategies = [
#                 (
#                     "DEFAULT",
#                     lambda: page.extract_text() or "",
#                 ),
#                 (
#                     "LOWER X TOLERANCE",
#                     lambda: page.extract_text(
#                         x_tolerance=1,
#                         y_tolerance=3,
#                     ) or "",
#                 ),
#                 (
#                     "LAYOUT",
#                     lambda: page.extract_text(
#                         layout=True,
#                     ) or "",
#                 ),
#             ]

#             for strategy_name, extract in strategies:
#                 print(f"\n--- {strategy_name} ---")
#                 print(extract())




# if __name__ == "__main__":
#     main()



import sys
from pathlib import Path

import pdfplumber

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

from src.text_cleaner import clean_extracted_text

PDF_PATH = (
    BASE_DIR
    / "data"
    / "exam-question.pdf"
)


def main() -> None:
    if not PDF_PATH.is_file():
        raise FileNotFoundError(f"PDF not found: {PDF_PATH}")

    with pdfplumber.open(PDF_PATH) as pdf:
        # Physical PDF pages 2, 3, 6 and 10.
        page_indices = (1, 2, 5, 9)

        for page_index in page_indices:
            if page_index >= len(pdf.pages):
                continue

            page = pdf.pages[page_index]

            raw_text = page.extract_text(
                x_tolerance=1,
                y_tolerance=3,
            ) or ""

            cleaned_text = clean_extracted_text(raw_text)

            print(f"\n{'=' * 70}")
            print(f"PDF PAGE {page_index + 1}")
            print("=" * 70)
            print(cleaned_text)


if __name__ == "__main__":
    main()
