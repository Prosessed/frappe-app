import frappe
from erpnext.stock.dashboard.item_dashboard import get_data
import frappe.utils

@frappe.whitelist()
def get_items_from_item_group(item_group:str=None, search_term:str=None, is_search:bool=False):
    """Get item list data by item group or item name search data

    Args:
        item_group (str, optional): Item Group Name. Defaults to None.
        search_term (str, optional): Item Name Search Data. Defaults to None.
        is_search (bool, optional): Condition for get items by item name search data. Defaults to False.

    Returns:
        returns item details with stock qty data.
    """
    if not item_group and not is_search:
        frappe.response["status_code"] = 400
        frappe.response["message"] = "Item Group Required"
        return

    if item_group and not frappe.db.get_value("Item Group", item_group):
        frappe.response["status_code"] = 500
        frappe.response["message"] = "Item Group Not Found"
        return

    items = []
    filters = {}

    if item_group and not is_search:
        filters["item_group"] = item_group
    elif is_search and search_term:
        filters = {'item_name':['like',f'%{search_term}%']}

    item_list = frappe.db.get_all("Item", filters, pluck="name")

    for item_code in item_list:
        price_list = {}
        price_list["buying_rate"] = frappe.db.get_value(
                                        "Item Price",
                                        {
                                        "buying" : 1,
                                        "item_code" : item_code
                                        },
                                        "price_list_rate"
                                        )
        price_list["selling_rate"] = frappe.db.get_value(
                                        "Item Price",
                                        {
                                        "selling" : 1,
                                        "item_code" : item_code
                                        },
                                        "price_list_rate"
                                        )

        item_details = frappe.db.get_value(
                            "Item",
                            item_code,
                            ["stock_uom", "brand", "image", "item_name","valuation_rate","description","sales_uom","item_group"],
                            as_dict=1
                            )
        list_of_uoms = frappe.db.get_all(
                            "UOM Conversion Detail",
                            {
                                "parent":item_code
                            },
                            ["uom", "conversion_factor"]
                            )

        item_barcodes = frappe.db.get_all(
                            "Item Barcode",
                            {
                                "parent":item_code
                            },
                            ["barcode", "barcode_type"]
                            )

        stock_data = get_data(item_code=item_code, item_group=item_group)

        list_of_stocks = []
        stock_qty = 0

        if stock_data:
            stock_qty = stock_data[0].get('actual_qty')
            for stock in stock_data:
                list_of_stocks.append({
                    "actual_qty" : stock.get('actual_qty'),
                    "warehouse" : stock.get('warehouse')
                })

        items.append({
            "item_code":item_code,
            "item_name": item_details.get('item_name'),
            "item_group": item_details.get('item_group'),
            "description": item_details.get('description'),
            "brand": item_details.get('brand'),
            "item_image": item_details.get('image'),
            "stock_uom": item_details.get('stock_uom'),
            "sales_uom": item_details.get('sales_uom'),
            "price_list": price_list,
            "actual_qty": stock_qty,
            "list_of_uoms": list_of_uoms,
            "list_of_stocks": list_of_stocks,
            "barcode": item_barcodes
        })

    frappe.response["message"] = items

#queries
@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_uom_list(doctype, txt, searchfield, start, page_len, filters):
	return frappe.db.sql("""
        select uom from `tabUOM Conversion Detail` where parent='{0}' and uom like '%{1}%'
	    """.format(filters.get("item_code"), txt))

@frappe.whitelist()
def check_si_against_so(so_name:str):
    linked_invoices = frappe.db.sql_list(
			"""select distinct t1.name
			from `tabSales Invoice` t1,`tabSales Invoice Item` t2
			where t1.name = t2.parent and t2.sales_order = %s and t1.docstatus = 0""",
			so_name,
		)

    if linked_invoices:
        return True

    return False