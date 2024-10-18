import frappe
from erpnext.stock.dashboard.item_dashboard import get_data
from erpnext.accounts.party import get_dashboard_info
from erpnext.accounts.report.customer_ledger_summary.customer_ledger_summary import execute as cls_execute
from frappe.utils import getdate


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


@frappe.whitelist()
def get_sales_person_customers(sales_person:str, limit_start:int=0, limit_page_length:int=100):
    """Get customer list with customer account details"""

    sales_person_name = frappe.utils.get_fullname(sales_person)
    customers = []

    # Fetch all customers at once
    customer_list = frappe.db.get_list("Customer", filters=[["Sales Team", "sales_person", "=", sales_person_name],
                     ["Sales Team", "parenttype", "=", "Customer"], ["disabled", "=", 0]], fields=["*"],
                     limit_start=limit_start, limit_page_length=limit_page_length)

    # Fetch all relevant sales orders and invoices for customers in one go
    customer_names = [customer.get('name') for customer in customer_list]
    so_data = frappe.db.get_all('Sales Order',
        {'customer': ('in', customer_names), 'docstatus': 1},
        ['customer', 'transaction_date', 'COUNT(name) as total_so_count'],
        group_by='customer',
        order_by='transaction_date DESC'
    )

    si_data = frappe.db.get_all('Sales Invoice',
        {'customer': ('in', customer_names)},
        pluck='name',
        group_by='customer'
    )

    # Create a mapping for easy lookup
    so_mapping = {data['customer']: data for data in so_data}
    si_mapping = {customer: [] for customer in customer_names}

    for si in si_data:
        customer_name = si
        if customer_name in si_mapping:
            si_mapping[customer_name].append(si)

    for customer in customer_list:
        customer_name = customer.get('name')

        # Fetch dashboard info
        dashboard_info = get_dashboard_info("Customer", customer_name, customer.get('loyalty_program')) or [{}]

        filters = frappe._dict({
            "from_date": customer.get('creation'),
            "to_date": getdate(),
            "customer": customer_name
        })

        cls_data = cls_execute(filters)[1] or [{}]

        # Fetch sales order data
        last_order_data = so_mapping.get(customer_name)
        last_order_date = last_order_data['transaction_date'] if last_order_data else None
        total_so_count = last_order_data['total_so_count'] if last_order_data else 0

        address_list = frappe.get_list(
            "Address",
            filters=[["Dynamic Link", "link_doctype", "=", "Customer"],
                     ["Dynamic Link", "link_name", "=", customer_name],
                     ["Dynamic Link", "parenttype", "=", "Address"]],
            fields=["address_title","address_type","address_line1","address_line2",
                    "city","state","country","pincode","email_id","phone","fax",
                    "is_primary_address","is_shipping_address","disabled","custom_note", "creation"],
            order_by="is_primary_address DESC, creation ASC",
        )

        email_id = ''
        if not customer.get('email') and address_list:
            email_id = address_list[0]["email_id"]


        contact_list = frappe.get_list(
            "Contact",
            filters=[["Dynamic Link", "link_doctype", "=", "Customer"],
                     ["Dynamic Link", "link_name", "=", customer_name],
                     ["Dynamic Link", "parenttype", "=", "Contact"]],
            fields=["full_name" , "phone", "mobile_no", "image", "is_primary_contact", "is_billing_contact", "creation"],
            order_by="is_primary_contact DESC, creation ASC",
        )

        phone = ''
        if not customer.get('mobile_no') and contact_list:
            phone = contact_list[0]['phone']

        customers.append({
            "customer_name": customer_name,
            "customer_group": customer.get('customer_group', ''),
            "phone_no": phone,
            "email": email_id,
            "customer_type": customer.get('customer_type', ''),
            "address_list": address_list,
            "contact_list": contact_list,
            "payment_terms": customer.get('payment_terms', ''),
            "total_payment_due": dashboard_info[0].get('total_unpaid', 0),
            "total_paid_amount": cls_data[0].get('paid_amount', 0),
            "invoiced_amount": cls_data[0].get('invoiced_amount', 0),
            "closing_balance": cls_data[0].get('closing_balance', 0),
            "opening_balance": cls_data[0].get('opening_balance', 0),
            "last_order_date": last_order_date,
            "total_so_count": total_so_count,
            "list_of_si": si_mapping.get(customer_name, []),
            "top_3_products": get_top_3_consecutive_products(customer_name)
        })

    return customers


def get_top_3_consecutive_products(customer):
    sales_orders = frappe.db.sql("""
        SELECT soi.item_code, soi.item_name, soi.image, so.transaction_date
        FROM `tabSales Order Item` soi
        JOIN `tabSales Order` so ON so.name = soi.parent
        WHERE so.customer = %s AND so.docstatus = 1
        ORDER BY so.transaction_date ASC
    """, (customer,), as_dict=True)

    if not sales_orders:
        return None

    # Initialize variables to track consecutive products
    consecutive_products = {}
    last_product = None
    consecutive_count = 0

    # Process each sales order
    for order in sales_orders:
        current_product = order["item_code"]
        item_image = order["image"]
        item_name = order["item_name"]

        # Check if the product is the same as the last ordered product
        if current_product == last_product:
            consecutive_count += 1
        else:
            # Reset count for new product
            consecutive_count = 1

        # Update the consecutive count in the dictionary
        if current_product in consecutive_products:
            consecutive_products[current_product]["count"] = max(consecutive_products[current_product]["count"], consecutive_count)
        else:
            consecutive_products[current_product] = {
                "count": consecutive_count,
                "item_image": item_image,
                "item_name": item_name,
                "item_code": current_product
            }

        # Set last_product for next iteration
        last_product = current_product

    # Sort products by consecutive count and get top 3
    sorted_products = sorted(consecutive_products.items(), key=lambda x: x[1]["count"], reverse=True)
    top_3_products = sorted_products[:3]

    # Return the top 3 products
    return [{"item_code": product[0], "item_name": product[1]["item_name"], "item_image": product[1]["item_image"]} for product in top_3_products]


@frappe.whitelist()
def get_sales_person_orders(sales_person:str, limit_start:int=0, limit_page_length:int=100):
    sales_person_name = frappe.utils.get_fullname(sales_person)

    # Fetch all sales order
    so_list = frappe.db.get_list("Sales Order", filters=[["Sales Team", "sales_person", "=", sales_person_name],
                     ["Sales Team", "parenttype", "=", "Sales Order"], ["docstatus", "=", 1]],
                     fields=["name", "owner", "transaction_date", "delivery_date", "order_type", "customer_name", "grand_total", "in_words", "workflow_state"],
                     limit_start=limit_start, limit_page_length=limit_page_length)

    if so_list:
        for so in so_list:
            if so.get('workflow_state') and so.get('workflow_state') == 'Invoiced':
                si_name = frappe.db.get_value("Sales Invoice Item", {"sales_order":so.get('name'), "docstatus":1}, 'parent')
                if si_name:
                    so["file"] = {}
                    pdf_file = frappe.get_print(doctype="Sales Invoice", name=si_name, print_format="Tax Invoice", as_pdf=True)
                    so["file"]["filename"] = f'{si_name}.pdf'
                    so["file"]["filecontent"] = pdf_file
                    so["file"]["type"] =  'pdf'

    return so_list