import pandas as pd


def normalize_question_table(
    table: list[list[str | None]],
) -> pd.DataFrame:
    """
    Normalize question-and-answer tables that pdfplumber
    extracts into nine columns instead of three.
    """
    df = pd.DataFrame(table)

    # Replace empty strings and whitespace with missing values.
    df = df.replace(r"^\s*$", pd.NA, regex=True)

    # Remove completely empty rows.
    df = df.dropna(axis=0, how="all").reset_index(drop=True)

    if df.empty:
        return df

    # Detect the nine-column Question / Answer / Marks layout.
    if df.shape[1] >= 9:
        header_row_index = next(
            (
                index
                for index, row in enumerate(df.fillna("").astype(str).values.tolist())
                if ("Question" in row and "Answer" in row and "Marks" in row)
            ),
            None,
        )

        if header_row_index is not None:
            normalized_rows: list[list[object]] = [["Question", "Answer", "Marks"]]

            # Extract question, answer, and marks.
            for row_index in range(
                header_row_index + 1,
                len(df),
            ):
                row = df.iloc[row_index].tolist()

                question_number = row[0] if len(row) > 0 else None
                answer_text = row[3] if len(row) > 3 else None
                marks = row[6] if len(row) > 6 else None

                question = (
                    str(question_number).strip() if pd.notna(question_number) else ""
                )
                answer = str(answer_text).strip() if pd.notna(answer_text) else ""
                mark_value = str(marks).strip() if pd.notna(marks) else ""

                # Ignore repeated headers and empty rows.
                if question == "Question":
                    continue

                if not question and not answer and not mark_value:
                    continue

                normalized_rows.append([question, answer, mark_value])

            return pd.DataFrame(normalized_rows)

    # Leave other table layouts unchanged.
    return df.dropna(axis=1, how="all")
