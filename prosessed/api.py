import frappe
from frappe import auth

@frappe.whitelist()
def get_inspection_form_pdf(docname):
	res = {}
	pdf_file = frappe.get_print(doctype="Inspection Form",name=docname, print_format="Inspection Report Format", as_pdf=True)
	res["filename"] = f'{docname}.pdf'
	res["filecontent"] = pdf_file
	res["type"] =  'pdf'

	frappe.response.message = res
	
	return frappe.response

@frappe.whitelist( allow_guest=True )
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