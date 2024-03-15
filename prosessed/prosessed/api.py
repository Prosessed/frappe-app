import frappe

@frappe.whitelist()
def get_inspection_form_pdf(docname):
    res = {}
	pdf_file = frappe.get_print(doctype="Inspection Form",name=docname, print_format="Inspection Report Format", as_pdf=True)
    res["filename"] = f'{docname}.pdf'
    res["filecontent"] = pdf_file
    res["type"] =  'pdf'

    frappe.response.message = res
    
    return frappe.response