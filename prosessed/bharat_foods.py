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
    filters = {"disabled":0}

    if item_group and not is_search:
        filters["item_group"] = item_group
    elif is_search and search_term:
        filters['item_name'] = ['like',f'%{search_term}%']

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
            projected_qty = stock_data[0].get('projected_qty')
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
            "projected_qty": projected_qty,
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
def get_sales_person_customers(sales_person:str, limit_start:int=0, limit_page_length:int=20):
    """Get customer list assigned for specific sales person

    Args:
        sales_person (str): sales person email
        limit_start (int, optional): limit start length for pagination. Defaults to 0.
        limit_page_length (int, optional): limit page length for pagination. Defaults to 100.

    Returns:
        list: returns the list of customer details.
    """

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
def get_sales_person_orders(sales_person:str=None, customer_name:str=None, workflow_state:str=None, docstatus:int=1, limit_start:int=0, limit_page_length:int=20):
    """Get the sales orders created by specific sales person.

    Args:
        sales_person (str): Sales Person Email ID
        limit_start (int, optional): limit start length for pagination. Defaults to 0.
        limit_page_length (int, optional): limit page length for pagination. Defaults to 20.

    Returns:
        list: returns the list of sales orders with invoice print format pdf
    """
    filters = [["docstatus", "=", docstatus]]

    if sales_person:
        sales_person_name = frappe.utils.get_fullname(sales_person)
        filters.append(["Sales Team", "sales_person", "=", sales_person_name])
        filters.append(["Sales Team", "parenttype", "=", "Sales Order"])

    if customer_name:
        filters.append(["customer_name", "=", customer_name])

    if workflow_state:
        filters.append(["workflow_state", "=", workflow_state])

    # Fetch all sales order
    so_list = frappe.db.get_list("Sales Order", filters=filters,
                     fields=["name", "transaction_date", "delivery_date", "order_type", "customer_name", "grand_total", "in_words", "workflow_state"],
                     limit_start=limit_start, limit_page_length=limit_page_length)

    if so_list:
        for so in so_list:
            so["sales_persons_involved"] = []

            if sales_team_list := frappe.db.get_list("Sales Team", {"parent":so.get('name'), "docstatus":1}, pluck='sales_person'):
                so["sales_persons_involved"].append(sales_team_list)

            if so.get('workflow_state') and so.get('workflow_state') == 'Invoiced':
                if si_list := frappe.db.get_list("Sales Invoice Item",
                    {"sales_order":so.get('name'), "docstatus":1}, pluck='parent'):
                    so["sales_invoice_list"] = []

                    for si in set(si_list):
                        invoice_id, si_workflow_state, grand_total, invoice_date = frappe.db.get_value("Sales Invoice", si, ["name", "workflow_state", "grand_total", "posting_date"])
                        so["sales_invoice_list"].append({
                            "invoice_id" : invoice_id,
                            "invoice_date" : invoice_date,
                            "workflow_state" : si_workflow_state,
                            "invoice_total" : grand_total
                        })

    return so_list


@frappe.whitelist()
def get_order_details(order_id:str, limit:int=10, offset:int=0):
    # SQL query to fetch order, sales team, and invoice details
    so_details = frappe.db.sql(
        """
        SELECT
            so.name AS order_id,
            so.customer_name,
            so.transaction_date AS order_date,
            so.grand_total AS order_grand_total,
            so.workflow_state AS order_workflow_status,
            so.docstatus AS order_doc_status,

            -- Fetch Sales Team Members (Salespersons)
            GROUP_CONCAT(st.sales_person SEPARATOR ', ') AS sales_person_list,

            si.name AS invoice_id,
            si.grand_total AS invoice_total,
            si.posting_date AS invoice_date,
            si.docstatus AS invoice_doc_status,
            si.due_date AS invoice_due_date,
            si.workflow_state AS invoice_workflow_status,

            sii.item_code AS item_name,
            sii.qty AS item_quantity,
            sii.uom,
            sii.rate

        FROM
            `tabSales Order` AS so
        LEFT JOIN
            `tabSales Invoice Item` AS sii ON sii.sales_order = so.name
        LEFT JOIN
            `tabSales Invoice` AS si ON sii.parent = si.name

        -- Join Sales Team table to get Salespersons for the Sales Order
        LEFT JOIN
            `tabSales Team` AS st ON st.parent = so.name

        WHERE
            so.name = %(sales_order_id)s

        -- Pagination Filters
        GROUP BY
            so.name, si.name, sii.item_code
        LIMIT %(limit)s OFFSET %(offset)s;
        """,
        {
            "sales_order_id": order_id,
            "limit": limit,
            "offset": offset
        },
        as_dict=True
    )

    # Restructure the result
    invoice_map = {}

    for row in so_details:
        invoice_id = row['invoice_id']

        # Check if the invoice is already added, if not create a new entry
        if invoice_id and invoice_id not in invoice_map:
            invoice_map[invoice_id] = {
                'invoice_id': invoice_id,
                'invoice_total': row['invoice_total'],
                'invoice_date': row['invoice_date'],
                'invoice_doc_status': row['invoice_doc_status'],
                'invoice_due_date': row['invoice_due_date'],
                'invoice_workflow_status': row['invoice_workflow_status'],
                'items': []
            }

            # Add the items to the relevant invoice
            invoice_map[invoice_id]['items'].append({
                'item_name': row['item_name'],
                'item_quantity': row['item_quantity'],
                'uom': row['uom'],
                'rate': row['rate']
            })

    # Prepare the final result: order details with sales invoices as a list
    result = {
        'order_id': so_details[0]['order_id'] if so_details else None,
        'customer_name': so_details[0]['customer_name'] if so_details else None,
        'order_date': so_details[0]['order_date'] if so_details else None,
        'order_grand_total': so_details[0]['order_grand_total'] if so_details else None,
        'order_workflow_status': so_details[0]['order_workflow_status'] if so_details else None,
        'order_doc_status': so_details[0]['order_doc_status'] if so_details else None,
        'sales_person_list': so_details[0]['sales_person_list'] if so_details else None,
        'invoices': list(invoice_map.values())
    }

    return result


@frappe.whitelist()
def get_sales_invoice_pdf(invoice_id):
    pdf_file = frappe.get_print(doctype="Sales Invoice", name=invoice_id, print_format="Tax Invoice", as_pdf=True)

    frappe.response["filename"] = f'{invoice_id}.pdf'
    frappe.response["filecontent"] = pdf_file
    frappe.response["type"] =  'pdf'


# @frappe.whitelist()
# def get_customer_listing(sales_person:str=None, payment_terms:str=None, limit:int=10, offset:int=1):
#     # Parse the filters
#     sales_person = frappe.utils.get_fullname(sales_person)

#     # SQL query to fetch customer data
#     query = """
#         SELECT
#             c.customer_name,
#             c.customer_group,
#             c.phone,
#             c.email_id,
#             COUNT(so.name) as total_sales_orders,
#             GROUP_CONCAT(DISTINCT sp.sales_person_name) as sales_persons,
#             GROUP_CONCAT(DISTINCT a.address_line1, ' ', a.city) as addresses,
#             c.payment_terms,
#             c.payment_terms_template
#         FROM `tabCustomer` c
#         LEFT JOIN `tabSales Order` so ON c.name = so.customer
#         LEFT JOIN `tabSales Team` st ON so.name = st.parent
#         LEFT JOIN `tabSales Person` sp ON st.sales_person = sp.name
#         LEFT JOIN `tabDynamic Link` dl ON dl.link_name = c.name AND dl.link_doctype = 'Customer'
#         LEFT JOIN `tabAddress` a ON dl.parent = a.name
#         WHERE c.disabled = 0
#     """

#     # Apply filters if provided
#     if sales_person:
#         query += " AND sp.sales_person_name = %(sales_person)s"
#     if payment_terms:
#         query += " AND c.payment_terms_template = %(payment_terms)s"

#     query += """
#         GROUP BY c.name
#         ORDER BY c.customer_name ASC
#         LIMIT %(limit)s OFFSET %(offset)s
#     """

#     # Execute the query with filters
#     data = frappe.db.sql(query, {
#         'sales_person': sales_person,
#         'payment_terms': payment_terms,
#         'limit': limit,
#         'offset': offset
#     }, as_dict=True)

#     # Total records count
#     count_query = """
#         SELECT COUNT(DISTINCT c.name)
#         FROM `tabCustomer` c
#         LEFT JOIN `tabSales Order` so ON c.name = so.customer
#         LEFT JOIN `tabSales Team` st ON so.name = st.parent
#         LEFT JOIN `tabSales Person` sp ON st.sales_person = sp.name
#         LEFT JOIN `tabDynamic Link` dl ON dl.link_name = c.name AND dl.link_doctype = 'Customer'
#         LEFT JOIN `tabAddress` a ON dl.parent = a.name
#         WHERE c.disabled = 0
#     """
#     if sales_person:
#         count_query += " AND sp.sales_person_name = %(sales_person)s"
#     if payment_terms:
#         count_query += " AND c.payment_terms_template = %(payment_terms)s"

#     total_records = frappe.db.sql(count_query, {
#         'sales_person': sales_person,
#         'payment_terms': payment_terms
#     })[0][0]

#     return {
#         'data': data,
#         'total_records': total_records
#     }


@frappe.whitelist()
def get_customer_list(sales_person:str=None, customer_id:str=None, payment_terms:str=None, limit_page_length:int=20, limit_start:int=0):
    sales_person_name = frappe.utils.get_fullname(sales_person)
    customers = []
    filters = [["disabled", "=", 0]]
    if customer_id:
        filters.append(["name", "=", customer_id])

    if sales_person:
        filters.append(["Sales Team", "sales_person", "=", sales_person_name])
        filters.append(["Sales Team", "parenttype", "=", "Customer"])

    if payment_terms:
        filters.append(["payment_terms", "=", payment_terms])

    fields = ["name","customer_name","customer_group","customer_type","payment_terms"]

    # Fetch all customers at once
    customer_list = frappe.db.get_list("Customer", filters=filters, fields=fields,
                     limit_start=limit_start, limit_page_length=limit_page_length)

    for customer in customer_list:
        customer_id = customer.get('name')
        # sales_persons_involved = []

        # if sales_team_list := frappe.db.get_list("Sales Team", {"parent":customer_id, "docstatus":1}, pluck='sales_person'):
        #     sales_persons_involved.append(sales_team_list)

        total_so_count = frappe.db.count("Sales Order", {"customer":customer_id})

        address_list = frappe.get_list(
            "Address",
            filters=[["Dynamic Link", "link_doctype", "=", "Customer"],
                     ["Dynamic Link", "link_name", "=", customer_id],
                     ["Dynamic Link", "parenttype", "=", "Address"]],
            fields=["address_title","address_type","address_line1","address_line2",
                    "city","state","country","pincode","email_id","phone","fax",
                    "is_primary_address","is_shipping_address","disabled","custom_note", "creation"],
            order_by="is_primary_address DESC, creation ASC",
        )

        address_list = frappe.db.sql(
        """
            SELECT
                a.name, dl.link_name, a.address_title, a.address_type, a.address_line1, a.address_line2,
                a.city, a.state, a.country, a.pincode, a.email_id, a.phone, a.fax, a.is_primary_address, a.is_shipping_address,
                a.disabled, a.creation
            FROM `tabAddress` a
            LEFT JOIN `tabDynamic Link` dl ON a.name = dl.link_name
            WHERE dl.link_doctype = 'Customer'
            AND dl.link_name IN %(customer_id)s
            AND dl.parenttype = 'Contact'
            ORDER BY a.is_primary_address DESC, a.creation ASC
        """,
        {"customer_id": customer_id},  # Convert customer_ids to a tuple for SQL IN clause
        as_dict=1
    )

        email_id = ''
        if not customer.get('email') and address_list:
            email_id = address_list[0]["email_id"]


        # contact_list = frappe.get_list(
        #     "Contact",
        #     filters=[["Dynamic Link", "link_doctype", "=", "Customer"],
        #              ["Dynamic Link", "link_name", "=", customer_id],
        #              ["Dynamic Link", "parenttype", "=", "Contact"]],
        #     fields=["full_name" , "phone", "mobile_no", "image", "is_primary_contact", "is_billing_contact", "creation"],
        #     order_by="is_primary_contact DESC, creation ASC",
        # )

        contact_list = frappe.db.sql(
        """
            SELECT
                c.name, dl.link_name, c.full_name, c.phone, c.mobile_no, c.image,
                c.is_primary_contact, c.is_billing_contact, c.creation
            FROM `tabContact` c
            LEFT JOIN `tabDynamic Link` dl ON c.name = dl.link_name
            WHERE dl.link_doctype = 'Customer'
            AND dl.link_name IN %(customer_id)s
            AND dl.parenttype = 'Contact'
            ORDER BY a.is_primary_contact DESC, a.creation ASC
        """,
        {"customer_id": customer_id},  # Convert customer_ids to a tuple for SQL IN clause
        as_dict=1
    )

        phone = ''
        if not customer.get('mobile_no') and contact_list:
            phone = contact_list[0]['phone']

        customers.append({
            "customer_name": customer.get('customer_name', ''),
            "customer_group": customer.get('customer_group', ''),
            "phone_no": phone,
            "email": email_id,
            "customer_type": customer.get('customer_type', ''),
            "address_list": address_list,
            "contact_list": contact_list,
            "payment_terms": customer.get('payment_terms', ''),
            "total_so_count": total_so_count if total_so_count else 0,
            # "sales_persons": sales_persons_involved
        })

    return customers


@frappe.whitelist()
def get_customer_lists(sales_person: str = None, customer_id: str = None, payment_terms: str = None, limit_page_length: int = 20, limit_start: int = 0):
    sales_person_name = frappe.utils.get_fullname(sales_person) if sales_person else None
    customers = []
    filters = [["disabled", "=", 0]]

    if customer_id:
        filters.append(["name", "=", customer_id])

    if sales_person_name:
        filters.append(["Sales Team", "sales_person", "=", sales_person_name])
        filters.append(["Sales Team", "parenttype", "=", "Customer"])

    if payment_terms:
        filters.append(["payment_terms", "=", payment_terms])

    fields = ["name", "customer_name", "customer_group", "customer_type", "payment_terms"]

    # Fetch customer list with pagination
    customer_list = frappe.db.get_list("Customer", filters=filters, fields=fields,
                                       limit_start=limit_start, limit_page_length=limit_page_length)

    # If no customers, return early
    if not customer_list:
        return []

    customer_ids = [c['name'] for c in customer_list]

    # Fetch related addresses in a single query
    # address_list = frappe.get_list(
    #     "Address",
    #     filters=[["Dynamic Link", "link_doctype", "=", "Customer"],
    #              ["Dynamic Link", "link_name", "in", customer_ids]],
    #     fields=["name", "address_title", "address_type", "address_line1", "address_line2",
    #             "city", "state", "country", "pincode", "email_id", "phone", "fax",
    #             "is_primary_address", "is_shipping_address", "disabled", "custom_note", "creation"],
    #     order_by="is_primary_address DESC, creation ASC"
    # )

    address_list = frappe.db.sql(
        """
            SELECT
                a.name, dl.link_name, a.address_title, a.address_type, a.address_line1, a.address_line2,
                a.city, a.state, a.country, a.pincode, a.email_id, a.phone, a.fax, a.is_primary_address, a.is_shipping_address,
                a.disabled, a.creation
            FROM `tabAddress` a
            LEFT JOIN `tabDynamic Link` dl ON a.name = dl.link_name
            WHERE dl.link_doctype = 'Customer'
            AND dl.link_name IN %(customer_ids)s
            AND dl.parenttype = 'Contact'
        """,
        {"customer_ids": tuple(customer_ids)},  # Convert customer_ids to a tuple for SQL IN clause
        as_dict=1
    )

    # Group addresses by customer ID
    address_by_customer = {customer_id: [] for customer_id in customer_ids}
    for addr in address_list:
        address_by_customer[addr['link_name']].append(addr)

    # Fetch related contacts in a single query
    # contact_list = frappe.get_list(
    #     "Contact",
    #     filters=[["Dynamic Link", "link_doctype", "=", "Customer"],
    #              ["Dynamic Link", "link_name", "in", customer_ids]],
    #     fields=["name", "full_name", "phone", "mobile_no", "image", "is_primary_contact",
    #             "is_billing_contact", "creation"],
    #     order_by="is_primary_contact DESC, creation ASC"
    # )

    contact_list = frappe.db.sql(
        """
            SELECT
                c.name, dl.link_name, c.full_name, c.phone, c.mobile_no, c.image,
                c.is_primary_contact, c.is_billing_contact, c.creation
            FROM `tabContact` c
            LEFT JOIN `tabDynamic Link` dl ON c.name = dl.link_name
            WHERE dl.link_doctype = 'Customer'
            AND dl.link_name IN %(customer_ids)s
            AND dl.parenttype = 'Contact'
        """,
        {"customer_ids": tuple(customer_ids)},  # Convert customer_ids to a tuple for SQL IN clause
        as_dict=1
    )


    # Group contacts by customer ID
    contact_by_customer = {customer_id: [] for customer_id in customer_ids}
    for contact in contact_list:
            contact_by_customer[contact['link_name']].append(contact)

    # Fetch sales order counts in bulk
    sales_order_counts = frappe.db.get_all("Sales Order", filters={"customer": ["in", customer_ids]},
                                           fields=["customer", "count(name) as total_so_count"],
                                           group_by="customer")

    so_count_by_customer = {so['customer']: so['total_so_count'] for so in sales_order_counts}

    # Build the final customer list
    for customer in customer_list:
        customer_id = customer.get('name')

        customers.append({
            "customer_name": customer.get('customer_name', ''),
            "customer_code": customer_id,
            "customer_group": customer.get('customer_group', ''),
            "phone_no": contact_by_customer[customer_id][0]['phone'] if contact_by_customer[customer_id] else '',
            "email": address_by_customer[customer_id][0]['email_id'] if address_by_customer[customer_id] else '',
            "customer_type": customer.get('customer_type', ''),
            "address_list": address_by_customer.get(customer_id, []),
            "contact_list": contact_by_customer.get(customer_id, []),
            "payment_terms": customer.get('payment_terms', ''),
            "total_so_count": so_count_by_customer.get(customer_id, 0),
        })

    return customers
