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

    if len(doc.get('items')):
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

def before_save_batch(doc, method=None):
    if not doc.expiry_date:
        if doc.reference_doctype and doc.reference_doctype == "Stock Entry":
            expiry_date, vendor_batch = frappe.db.get_value("Stock Entry Detail",
                            {"parent":doc.reference_name, "item_code":doc.item},
                            ["custom_expiry_date", "custom_vendor_batch"]
                            )

            if expiry_date:
                doc.expiry_date = expiry_date

            if vendor_batch:
                doc.custom_vendor_batch = vendor_batch


