import frappe
from erpnext.buying.doctype.purchase_order.purchase_order import make_purchase_receipt
from erpnext.stock.doctype.batch.batch import make_batch


def update_sales_order_workflow_state(doc, method=None):
    sales_order = str()
    if doc.doctype == "Work Order" and doc.sales_order:
        sales_order = doc.sales_order
    elif doc.items:
        for item in doc.items:
            if item.sales_order:
                sales_order = item.sales_order
                break

    if sales_order and (doc.docstatus == 0 and method == "validate") or (
        doc.doctype == "Sales Invoice" and doc.docstatus == 1) or (
        doc.doctype == "Work Order" and doc.workflow_state == "Production Completed"):
        frappe.db.set_value("Sales Order",
            {
                "name":sales_order
            },
            "workflow_state",
            doc.workflow_state,
            update_modified=False
        )


def update_purchase_order_workflow_state(doc, method=None):
    purchase_order = str()
    if doc.items:
        for item in doc.items:
            if item.purchase_order:
                purchase_order = item.purchase_order
                break

    if purchase_order and doc.docstatus == 1:
        frappe.db.set_value("Purchase Order",
            {
                "name":purchase_order
            },
            "workflow_state",
            doc.workflow_state,
            update_modified=False
        )


def update_work_order_workflow_state(doc, method=None):
    if doc.stock_entry_type in ["Material Transfer", "Manufacture", "Material Transfer for Manufacture"] and doc.work_order:
        workflow_state = "In Kitchen" if doc.stock_entry_type in ["Material Transfer", "Material Transfer for Manufacture"] else "Production Completed"

        doc = frappe.get_doc("Work Order", doc.work_order)
        doc.workflow_state = workflow_state
        doc.save()
        doc.submit()


def create_purchase_receipt(doc, method=None):
    allow_receipt = False
    for item in doc.items:
        if item.delivered_by_supplier != 1:
            allow_receipt = True
            break

    if doc.status not in ["Closed", "On Hold"] and (doc.per_received < 100 and allow_receipt):
        if doc.docstatus == 1 and doc.workflow_state == "Incoming Goods":
            pr_doc = make_purchase_receipt(doc.name)
            pr_doc.save()


def before_save_batch(doc, method=None):
    if doc.reference_doctype and doc.reference_doctype == "Purchase Receipt":
        expiry_date, vendor_batch = frappe.db.get_value("Purchase Receipt Item",
                        {"parent":doc.reference_name, "item_code":doc.item},
                        ["custom_expiry_date", "custom_vendor_batch"]
                        )

        if expiry_date:
            doc.expiry_date = expiry_date

        # if vendor_batch:
        #     doc.custom_vendor_batch = vendor_batch


def create_item_wise_batch(doc, method=None):
    if doc.doctype in ["Purchase Receipt", "Stock Entry"]:

        if doc.doctype == "Stock Entry" and doc.stock_entry_type not in ["Manufacture", "Material Receipt", "Repack"]:
            return

        for item in doc.items:
            if not frappe.db.get_value('Item', item.item_code, "create_new_batch"):
                if not item.custom_vendor_batch:
                    frappe.throw("Vendor Batch Error", f"Enter Vendor Batch on Item {item.item_code} for Batch Creation")

                if not item.custom_expiry_date:
                    frappe.throw("Expiry Date Error", f"Enter Expiry Date on Item {item.item_code} for Batch Creation")

                batch_no = make_batch(
                            frappe._dict(
                                {
                                    "item": item.item_code,
                                    "batch_id": item.custom_vendor_batch,
                                    "expiry_date": item.custom_expiry_date,
                                    "reference_doctype": doc.doctype,
                                    "reference_name": doc.name,
                                }
                            )
                        )
                item.batch_no = batch_no

def create_batch(doc, method=None):
     if doc.doctype == "Stock Entry":

        if doc.stock_entry_type not in ["Manufacture", "Material Receipt", "Repack"]:
            return

        for item in doc.items:
            if not frappe.db.get_value('Item', item.item_code, "create_new_batch") and not item.batch_no:
                if not item.custom_vendor_batch:
                    frappe.throw("Vendor Batch Error", f"Enter Vendor Batch on Item {item.item_code} for Batch Creation")

                if not item.custom_expiry_date:
                    frappe.throw("Expiry Date Error", f"Enter Expiry Date on Item {item.item_code} for Batch Creation")

                batch_no = make_batch(
                            frappe._dict(
                                {
                                    "item": item.item_code,
                                    "batch_id": item.custom_vendor_batch,
                                    "expiry_date": item.custom_expiry_date,
                                    "reference_doctype": doc.doctype,
                                    "reference_name": doc.name,
                                }
                            )
                        )

                item.batch_no = batch_no
                frappe.log_error("batch no", f"{item.item_name} and {item.batch_no}")