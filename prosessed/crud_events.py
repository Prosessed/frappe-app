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

def on_submit_stock_entry(doc, method=None):
    print("------------------------",doc)
    if isinstance(doc, object):
        doc = doc.as_dict()

    if doc.items.length:
        for item in doc.get('items'):
            if item.custom_expiry_date and item.serial_and_batch_bundle:
                batch_list = frappe.db.get_list(
                                "Serial and Batch Entry",
                                {"parent":item.serial_and_batch_bundle},
                                pluck="batch_no"
                                )

                for batch_no in batch_list:
                    if item.custom_vendor_batch:
                        frappe.db.set_value("Batch",
                            batch_no,
                            {
                                "expiry_date":item.custom_expiry_date,
                                "custom_vendor_batch":item.custom_vendor_batch
                            },
                            update_modified=False
                            )
                    else:
                        frappe.db.set_value("Batch",
                            batch_no, "expiry_date",
                            item.custom_expiry_date, update_modified=False
                            )