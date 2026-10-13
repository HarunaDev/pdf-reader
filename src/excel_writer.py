
from pathlib import Path

import pandas as pd


def save_tables_to_excel(
    tables: list[dict[str, object]],
    output_path: Path,
) -> None:
    """Save each extracted table to its own Excel worksheet."""

    if not tables:
        print("No tables were detected in the PDF.")
        return

    # Ensure the destination directory exists.
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with pd.ExcelWriter(
        output_path,
        engine="openpyxl",
    ) as writer:
        for table in tables:
            page_number = int(table["page"])
            table_number = int(table["table_number"])
            df = table["dataframe"]

            if not isinstance(df, pd.DataFrame):
                continue

            sheet_name = (
                f"Page{page_number}_Table{table_number}"
            )

            df.to_excel(
                writer,
                sheet_name=sheet_name[:31],
                index=False,
                header=False,
            )

    # print(f"Extracted {len(tables)} table(s).")
    # print(f"Excel file saved to: {output_path}")
