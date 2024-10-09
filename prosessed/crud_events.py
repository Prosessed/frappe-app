import frappe
from erpnext.buying.doctype.purchase_order.purchase_order import make_purchase_receipt

def update_sales_order_workflow_state(doc, method=None):
    sales_order = str()
    if doc.items:
        for item in doc.items:
            if item.sales_order:
                sales_order = item.sales_order
                break

    if sales_order and (doc.docstatus == 0 and method == "validate") or (
        doc.doctype == "Sales Invoice" and doc.docstatus == 1) or (
        doc.doctype == "Work Order" and doc.docstatus == 1 and doc.workflow_state == "Production Completed"):
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

    if purchase_order and (doc.docstatus == 0 and method == "validate") or  doc.docstatus == 1:
        frappe.db.set_value("Sales Order",
            {
                "name":purchase_order
            },
            "workflow_state",
            doc.workflow_state,
            update_modified=False
        )

def create_purchase_receipt(doc, method=None):
    if doc.docstatus == 1 and doc.workflow_state == "Incoming Goods":
        pr_doc = make_purchase_receipt(doc.name)
        pr_doc.save()
