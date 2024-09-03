import frappe

def validate_sales_order(doc, method=None):
    gross_profit = 0.0
    gross_profit_percent = 0.0

    for item in doc.items:
        gross_profit += item.gross_profit

    if doc.total > 0:
        gross_profit_percent = (gross_profit * 100) / doc.total

    doc.custom_gross_profit = gross_profit
    doc.custom_gross_profit_ = gross_profit_percent