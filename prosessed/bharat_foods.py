import frappe
from erpnext.stock.dashboard.item_dashboard import get_data
import frappe.utils

@frappe.whitelist()
def get_items_from_item_group(item_group=None):
    if not item_group:
        frappe.response["status_code"] = 400
        frappe.response["message"] = "Item Group Required"
        return

    if not frappe.db.get_value("Item Group", item_group):
        frappe.response["status_code"] = 500
        frappe.response["message"] = "Item Group Not Found"
        return

    items = []
    item_list = frappe.db.get_all("Item", {"item_group":item_group}, pluck="name")

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
                            ["stock_uom", "brand", "image", "item_name","valuation_rate","description"],
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
            "item_code" :item_code,
            "item_name" : item_details.get('item_name'),
            "description" : item_details.get('description')
            "brand" : item_details.get('brand'),
            "item_image" : item_details.get('image'),
            "stock_uom" : item_details.get('stock_uom'),
            "price_list" : price_list,
            "actual_qty" : stock_qty,
            "list_of_uoms" : list_of_uoms,
            "list_of_stocks" : list_of_stocks,
            "barcode" : item_barcodes
        })

    frappe.response["message"] = items