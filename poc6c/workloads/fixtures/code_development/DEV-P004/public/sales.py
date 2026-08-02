"""CSV sales summarization."""


def summarize_sales(text):
    """Group sales amounts by region."""

    lines = [line for line in text.splitlines() if line.strip()]
    if not lines or lines[0].strip() != "region,amount":
        raise ValueError("invalid CSV header")
    totals = {}
    for line in lines[1:]:
        pieces = line.split(",")
        if len(pieces) != 2:
            raise ValueError("invalid CSV row")
        region, amount_text = pieces
        try:
            amount = float(amount_text.strip())
        except ValueError as exc:
            raise ValueError("invalid amount") from exc
        totals[region] = totals.get(region, 0.0) + amount
    return totals
