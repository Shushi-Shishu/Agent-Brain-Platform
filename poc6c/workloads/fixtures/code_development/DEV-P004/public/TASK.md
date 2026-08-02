# Summarize CSV sales

`summarize_sales(text)` receives CSV text with the exact header
`region,amount`. Return a dictionary mapping each region to the sum of its
amounts.

CSV quoting rules must be respected, blank rows should be ignored, whitespace
around amounts is allowed, and an invalid header or non-numeric amount must
raise `ValueError`. Use only the Python standard library.
