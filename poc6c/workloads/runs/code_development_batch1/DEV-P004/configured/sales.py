"""CSV sales summarization."""

import csv
import io


def summarize_sales(text):
    """Group sales amounts by region."""

    totals = {}
    header_seen = False
    try:
        rows = csv.reader(io.StringIO(text, newline=""), strict=True)
        for row in rows:
            if not row or (len(row) == 1 and not row[0].strip()):
                continue
            if not header_seen:
                if row != ["region", "amount"]:
                    raise ValueError("invalid CSV header")
                header_seen = True
                continue
            if len(row) != 2:
                raise ValueError("invalid CSV row")
            region, amount_text = row
            try:
                amount = float(amount_text.strip())
            except ValueError as exc:
                raise ValueError("invalid amount") from exc
            totals[region] = totals.get(region, 0.0) + amount
    except csv.Error as exc:
        raise ValueError("invalid CSV") from exc

    if not header_seen:
        raise ValueError("invalid CSV header")
    return totals
