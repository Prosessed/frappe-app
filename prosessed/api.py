import frappe
from frappe import auth
from frappe.utils import cint
from frappe.utils.nestedset import get_root_of
from erpnext.stock.utils import scan_barcode
from typing import Dict, Optional

@frappe.whitelist()
def get_inspection_form_pdf(docname):
	res = {}
	pdf_file = frappe.get_print(doctype="Inspection Form",name=docname, print_format="Inspection Report Format", as_pdf=True)
	res["filename"] = f'{docname}.pdf'
	res["filecontent"] = pdf_file
	res["type"] =  'pdf'

	frappe.response["message"] = res

@frappe.whitelist(allow_guest=True)
def login(usr, pwd):
	try:
		login_manager = frappe.auth.LoginManager()
		login_manager.authenticate(user=usr, pwd=pwd)
		login_manager.post_login()
	except frappe.exceptions.AuthenticationError:
		frappe.clear_messages()
		frappe.local.response["message"] = {
			"success_key":0,
			"message":"Authentication Error!"
		}

		return

	api_generate = generate_keys(frappe.session.user)
	user = frappe.get_doc('User', frappe.session.user)

	frappe.response["message"] = {
		"success_key":1,
		"message":"Authentication success",
		"sid":frappe.session.sid,
		"api_key":user.api_key,
		"api_secret":api_generate,
		"username":user.username,
		"email":user.email
	}

def generate_keys(user):
	user_details = frappe.get_doc('User', user)
	api_secret = frappe.generate_hash(length=15)

	if not user_details.api_key:
		api_key = frappe.generate_hash(length=15)
		user_details.api_key = api_key

	user_details.api_secret = api_secret
	user_details.save()

	return api_secret

@frappe.whitelist(allow_guest=True)
def signup(**kwargs):
	data = {"message":""}
	if not kwargs["first_name"]:
		data["message"] = "Name cannot be null"
		return data

	if not kwargs["email"]:
		data["message"] = "Email cannot be null"
		return data

	if not kwargs["password"]:
		data["message"] = "Password cannot be null"
		return data

	if frappe.db.get_value("User", kwargs["email"]):
		data["message"] = "Email Id Already Exists"
		return data

	user = frappe.new_doc("User")
	user.email = kwargs["email"]
	user.first_name = kwargs["first_name"]
	user.send_welcome_email = 0
	user.user_type = 'System User'

	user.save(ignore_permissions=True)
	user.new_password = kwargs["password"]
	user.save(ignore_permissions = True)
	user.add_roles('System Manager')

	data["message"] = "Account Created, Please Login"

	frappe.response["message"] = {
		"success_key" : 1,
		"message" : data["message"]
	}

@frappe.whitelist()
def search_for_serial_or_batch_or_barcode_number(search_value: str) -> Dict[str, Optional[str]]:
	return scan_barcode(search_value)

def search_by_term(search_term):
	result = search_for_serial_or_batch_or_barcode_number(search_term) or {}
	item_code = result.get("item_code", search_term)
	serial_no = result.get("serial_no", "")
	batch_no = result.get("batch_no", "")
	barcode = result.get("barcode", "")
	if not result:
		return
	item_doc = frappe.get_doc("Item", item_code)
	if not item_doc:
		return
	item = {
		"barcode": barcode,
		"batch_no": batch_no,
		"description": item_doc.description,
		"is_stock_item": item_doc.is_stock_item,
		"item_code": item_doc.name,
		"item_image": item_doc.image,
		"item_name": item_doc.item_name,
		"serial_no": serial_no,
		"stock_uom": item_doc.stock_uom,
		"uom": item_doc.stock_uom,
	}
	if barcode:
		barcode_info = next(filter(lambda x: x.barcode == barcode, item_doc.get("barcodes", [])), None)
		if barcode_info and barcode_info.uom:
			uom = next(filter(lambda x: x.uom == barcode_info.uom, item_doc.uoms), {})
			item.update(
				{
					"uom": barcode_info.uom,
					"conversion_factor": uom.get("conversion_factor", 1),
				}
			)

	item_stock_qty = frappe.db.get_value("Bin", {"item_code":item_code},"actual_qty")
	item_stock_qty = item_stock_qty if item_stock_qty else 0 // item.get("conversion_factor", 1)
	item.update({"actual_qty": item_stock_qty})

	price = frappe.get_list(
		doctype="Item Price",
		filters={
			"item_code": item_code,
		},
		fields=["uom", "currency", "price_list_rate"],
	)

	def __sort(p):
		p_uom = p.get("uom")
		if p_uom == item.get("uom"):
			return 0
		elif p_uom == item.get("stock_uom"):
			return 1
		else:
			return 2

	# sort by fallback preference. always pick exact uom match if available
	price = sorted(price, key=__sort)
	if len(price) > 0:
		p = price.pop(0)
		item.update(
			{
				"currency": p.get("currency"),
				"price_list_rate": p.get("price_list_rate"),
			}
		)
	return {"items": [item]}

def add_search_fields_condition(search_term):
	condition = ""
	search_fields = frappe.get_all("POS Search Fields", fields=["fieldname"])
	if search_fields:
		for field in search_fields:
			condition += " or item.`{0}` like {1}".format(
				field["fieldname"], frappe.db.escape("%" + search_term + "%")
			)
	return condition

def get_conditions(search_term):
	condition = "("
	condition += """item.name like {search_term}
		or item.item_name like {search_term}""".format(
		search_term=frappe.db.escape("%" + search_term + "%")
	)
	condition += add_search_fields_condition(search_term)
	condition += ")"

	return condition

@frappe.whitelist()
def get_items(start, page_length, item_group, search_term=""):
	# warehouse, hide_unavailable_items = frappe.db.get_value(
	# 	"POS Profile", pos_profile, ["warehouse", "hide_unavailable_items"]
	# )
	hide_unavailable_items =False
	result = []

	if search_term:
		result = search_by_term(search_term) or []
		if result:
			return result

	if not frappe.db.exists("Item Group", item_group):
		item_group = get_root_of("Item Group")

	condition = get_conditions(search_term)
	# condition += get_item_group_condition(pos_profile)
	lft, rgt = frappe.db.get_value("Item Group", item_group, ["lft", "rgt"])
	print("left and right :", lft, rgt)
	bin_join_selection, bin_join_condition = "", ""
	if hide_unavailable_items:
		bin_join_selection = ", `tabBin` bin"
		bin_join_condition = (
			"AND bin.item_code = item.name AND bin.actual_qty > 0"
		)

	items_data = frappe.db.sql(
		"""
		SELECT
			item.name AS item_code,
			item.item_name,
			item.description,
			item.stock_uom,
			item.image AS item_image,
			item.is_stock_item

		FROM
			`tabItem` item {bin_join_selection}
		WHERE
			item.disabled = 0
			AND item.has_variants = 0
			AND item.is_sales_item = 1
			AND item.is_stock_item = 1
			AND item.is_fixed_asset = 0
			AND item.item_group in (SELECT name FROM `tabItem Group` WHERE lft >= {lft} AND rgt <= {rgt})
			AND {condition}
			{bin_join_condition}
		ORDER BY
			item.name asc
		LIMIT
			{page_length} offset {start}""".format(
			start=cint(start),
			page_length=cint(page_length),
			lft=cint(lft),
			rgt=cint(rgt),
			condition=condition,
			bin_join_selection=bin_join_selection,
			bin_join_condition=bin_join_condition,
		),
		as_dict=1,
	)

	if items_data:
		items = [d.item_code for d in items_data]
		item_prices_data = frappe.get_all(
			"Item Price",
			fields=["item_code", "price_list_rate", "currency"],
			filters={"item_code": ["in", items]},
		)

		item_prices = {}
		for d in item_prices_data:
			item_prices[d.item_code] = d

		for item in items_data:
			item_code = item.item_code
			item_price = item_prices.get(item_code) or {}
			is_qty_available = frappe.db.get_value("Bin", {"item_code":item_code},["actual_qty", "warehouse"])
			item_stock_qty, warehouse = is_qty_available if is_qty_available else [False, False]
			if not item_stock_qty:
				item_stock_qty = 0
			if not warehouse:
				warehouse= None

			row = {}
			row.update(item)
			row.update(
				{
					"price_list_rate": item_price.get("price_list_rate"),
					"currency": item_price.get("currency"),
					"actual_qty": item_stock_qty,
					"warehouse": warehouse
				}
			)
			result.append(row)
	# print("items :", result)
	return {"items": result}