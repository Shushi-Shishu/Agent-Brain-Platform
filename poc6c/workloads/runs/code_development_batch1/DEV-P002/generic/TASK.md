# Calculate invoice totals

Implement the existing `invoice_total(lines, tax_rate)` contract correctly.
Each line is a mapping with `unit_price`, `quantity`, and `discount_rate`.

The line discount applies before tax. Add the discounted line subtotals, apply
tax once to that sum, and round only the final result to two decimal places.
Reject negative quantities or rates outside the inclusive range 0 to 1 by
raising `ValueError`.
