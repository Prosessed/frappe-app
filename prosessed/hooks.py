app_name = "prosessed"
app_title = "Prosessed"
app_publisher = "Prosessed"
app_description = "Proseesed"
app_email = "care@prosessed.com"
app_license = "mit"
# required_apps = []

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/prosessed/css/prosessed.css"
# app_include_js = "/assets/prosessed/js/prosessed.js"

# include js, css files in header of web template
# web_include_css = "/assets/prosessed/css/prosessed.css"
# web_include_js = "/assets/prosessed/js/prosessed.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "prosessed/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"Sales Order" : "public/js/sales_order.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# fixtures = [{"doctype": "Client Script", "filters": [["module" , "in" , ("Prosessed")]]},{"doctype": "Server Script", "filters": [["module" , "in" , ("Prosessed")]]},{"doctype": "Workflow State"}, {"doctype": "Workflow Action Master"}, {"doctype": "Workflow Action"}, {"doctype": "Workflow"}]

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "prosessed/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
#	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
#	"methods": "prosessed.utils.jinja_methods",
#	"filters": "prosessed.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "prosessed.install.before_install"
# after_install = "prosessed.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "prosessed.uninstall.before_uninstall"
# after_uninstall = "prosessed.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "prosessed.utils.before_app_install"
# after_app_install = "prosessed.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "prosessed.utils.before_app_uninstall"
# after_app_uninstall = "prosessed.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "prosessed.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
#	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
#	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
#	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
	"Sales Invoice": {
		"on_submit": "prosessed.crud_events.update_sales_order_workflow_state",
		"on_update_after_submit": "prosessed.crud_events.update_sales_order_workflow_state"
	},
	"Work Order": {
	    "on_update_after_submit": "prosessed.crud_events.update_sales_order_workflow_state"
	},
	"Purchase Receipt": {
	    "before_submit" : "prosessed.crud_events.create_item_wise_batch",
	    "on_submit": "prosessed.crud_events.update_purchase_order_workflow_state"
	},
	"Purchase Order": {
	    "on_submit" : "prosessed.crud_events.create_purchase_receipt"
	},
	"Batch": {
		"before_save" : "prosessed.crud_events.before_save_batch"
	},
	"Stock Entry": {
		"validate" : "prosessed.crud_events.create_batch",
		# "before_submit" : "prosessed.crud_events.create_item_wise_batch",
		"on_submit" : "prosessed.crud_events.update_work_order_workflow_state"
	}
}

# Scheduled Tasks
# ---------------

# scheduler_events = {
#	"all": [
#		"prosessed.tasks.all"
#	],
#	"daily": [
#		"prosessed.tasks.daily"
#	],
#	"hourly": [
#		"prosessed.tasks.hourly"
#	],
#	"weekly": [
#		"prosessed.tasks.weekly"
#	],
#	"monthly": [
#		"prosessed.tasks.monthly"
#	],
# }

# Testing
# -------

# before_tests = "prosessed.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
#	"frappe.desk.doctype.event.event.get_events": "prosessed.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
#	"Task": "prosessed.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["prosessed.utils.before_request"]
# after_request = ["prosessed.utils.after_request"]

# Job Events
# ----------
# before_job = ["prosessed.utils.before_job"]
# after_job = ["prosessed.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
#	{
#		"doctype": "{doctype_1}",
#		"filter_by": "{filter_by}",
#		"redact_fields": ["{field_1}", "{field_2}"],
#		"partial": 1,
#	},
#	{
#		"doctype": "{doctype_2}",
#		"filter_by": "{filter_by}",
#		"partial": 1,
#	},
#	{
#		"doctype": "{doctype_3}",
#		"strict": False,
#	},
#	{
#		"doctype": "{doctype_4}"
#	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
#	"prosessed.auth.validate"
# ]
