import frappe
from erpnext.buying.doctype.purchase_order.purchase_order import make_purchase_receipt

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
    frappe.log_error("update_po_ws", f"{doc.docstatus} & {doc.workflow_state}")
    purchase_order = str()
    if doc.items:
        for item in doc.items:
            if item.purchase_order:
                purchase_order = item.purchase_order
                break

    if purchase_order and doc.docstatus == 1:
	frappe.log_error("update_po_ws")
        frappe.db.set_value("Purchase Order",
            {
                "name":purchase_order
            },
            "workflow_state",
            doc.workflow_state,
            update_modified=False
        )

def create_purchase_receipt(doc, method=None):
    allow_receipt = False
    for item in doc.items:
        if item.delivered_by_supplier != 1:
            allow_receipt = True
            break

    if doc.status not in ["Closed", "On Hold"] and (doc.per_received < 100 and allow_receipt):
        frappe.log_error("entered hooks", f"{doc.docstatus} & {doc.workflow_state}")
        if doc.docstatus == 1 and doc.workflow_state == "Incoming Goods":
            pr_doc = make_purchase_receipt(doc.name)
            pr_doc.save()
