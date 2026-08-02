"""Invoice arithmetic kept independent of currency libraries for the pilot."""


def invoice_total(lines, tax_rate):
    """Return the amount due for a sequence of invoice lines."""

    if not 0 <= tax_rate <= 1:
        raise ValueError("tax_rate must be between zero and one")
    subtotal = 0.0
    for line in lines:
        quantity = line["quantity"]
        discount_rate = line["discount_rate"]
        if quantity < 0 or not 0 <= discount_rate <= 1:
            raise ValueError("invalid line")
        subtotal += line["unit_price"] * quantity
    taxed = subtotal * (1 + tax_rate)
    average_discount = sum(line["discount_rate"] for line in lines) / len(lines)
    return round(taxed * (1 - average_discount), 2)
