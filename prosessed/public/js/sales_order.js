frappe.ui.form.on("Sales Order", {
    refresh : (frm) => {
        if (frm.doc.docstatus !== 1){
            frm.trigger("load_item_card")
        }
        frm.trigger('set_gross_profit_color')
    },
    set_gross_profit_color : (frm) => {
        const gross_profit = frm.doc.custom_gross_profit_
        let component = frm.get_field('custom_gross_profit_').$input_wrapper.find('.control-value')

        if (gross_profit < 0) {
            component.css('color', 'red')
        } else if (gross_profit > 0 && gross_profit < 25) {
            component.css('color', 'orange')
        } else if (gross_profit > 25) {
            component.css('color', 'green')
        }

    },

    load_item_card : (frm) => {
        var item_group, search_term, warehouse;
        warehouse = frm.doc.set_warehouse
        var wrapper = frm.get_field("custom_item_card").$wrapper;
          wrapper.html("")
          wrapper.append(
			`<div class="point-of-sale-app">
			<section class="items-selector">
				<div class="filter-section">
					<div class="label">${__('Item Card')}</div>
					<div class="search-field"></div>
					<div class="item-group-field"></div>
				</div>
				<div class="items-container"></div>
			</section>
            </div>`
		);
		frm.$component = wrapper.find('.items-selector');
		frm.$items_container = wrapper.find('.items-container');
        frm.$component.css({
            "grid-column": "span 12/span 12",
            "display": "flex",
            "flex-direction": "column",
            "overflow": "hidden",
            "height": "25rem",
        })
        frm.$component.attr('style', "grid-column : span 12/span 12 !important; display : flex !important; flex-direction: column !important; overflow: hidden !important; height: 42rem !important; min-height: 18rem !important;")
        load_item_data();
        make_search_bar();
        function load_item_data() {
            get_items({search_term, warehouse}).then(({message}) => {
                render_item_list(message.items);
            });
        }
        function get_items({start = 0, page_length = 40, search_term='', warehouse = ''}) {
            // const doc = this.events.get_frm().doc;
            // let { item_group, pos_profile } = this;
            // !item_group && (item_group = this.parent_item_group);
            if (!item_group){
                item_group = "All Item Group"
            }

            return frappe.call({
                method: "prosessed.api.get_items",
                freeze: true,
                args: { start, page_length, item_group, search_term, warehouse },
            });
        }

        function render_item_list(items) {
            frm.$items_container.html('');

            items.forEach(item => {
                const item_html = get_item_html(item);
                frm.$items_container.append(item_html);
            });
        }

        function get_item_html(item) {
            const me = this;
            // eslint-disable-next-line no-unused-vars
            const { item_image, serial_no, batch_no, barcode, actual_qty, stock_uom, price_list_rate, warehouse } = item;
            const precision = flt(price_list_rate, 2) % 1 != 0 ? 2 : 0;
            let indicator_color;
            let qty_to_display = actual_qty;


            if (item.is_stock_item) {
                indicator_color = (actual_qty > 10 ? "green" : actual_qty <= 0 ? "red" : "orange");

                if (Math.round(qty_to_display) > 999) {
                    qty_to_display = Math.round(qty_to_display)/1000;
                    qty_to_display = qty_to_display.toFixed(1) + 'K';
                }
            } else {
                indicator_color = '';
                qty_to_display = '';
            }

            function get_item_image_html() {
                if (item_image) {
                    return `
                        <div class="item-qty-pill">
							<span class="indicator-pill whitespace-nowrap ${indicator_color}">${qty_to_display}</span>
						</div>
                        <div class="flex items-center justify-center h-75 border-b-grey text-6xl text-grey-100">
                            <img
                                onerror="cur_pos.item_selector.handle_broken_image(this)"
                                class="h-full item-img" src="${item_image}"
                                alt="${frappe.get_abbr(item.item_name)}"
                            >
                        </div>`;
                } else {
                    return `
                        <div class="item-qty-pill">
							<span class="indicator-pill whitespace-nowrap ${indicator_color}">${qty_to_display}</span>
						</div>
                        <div class="item-display abbr">${frappe.get_abbr(item.item_name)}</div>`;
                }
            }

            return (
                `<div class="item-wrapper pt-3"
                    style="height:14rem;"
                    data-item-code="${escape(item.item_code)}" data-serial-no="${escape(serial_no)}"
                    data-batch-no="${escape(batch_no)}" data-uom="${escape(stock_uom)}"
                    data-rate="${escape(price_list_rate || 0)}" data-warehouse="${escape(item.warehouse)}"
                    title="${item.item_name}">

                    ${get_item_image_html()}

                    <div class="item-detail" style = "height:fit-content !important; padding:0.5rem;">
                        <div class="item-name" style = "overflow:normal !important; white-space:normal !important;">
                            ${item.item_name}
                        </div>
                    </div>
                </div>`
            );
        }

        function make_search_bar() {
            // const me = this;
            // const doc = me.events.get_frm().doc;
            frm.$component.find('.search-field').html('');
            frm.$component.find('.item-group-field').html('');

            frm.search_field = frappe.ui.form.make_control({
                df: {
                    label: __('Search'),
                    fieldtype: 'Data',
                    placeholder: __('Search by item code, serial number or barcode'),
                    onchange: function() {
                        search_term = this.value;
                        load_item_data();
                    },
                },
                parent: frm.$component.find('.search-field'),
                render_input: true,
            });
            frm.item_group_field = frappe.ui.form.make_control({
                df: {
                    label: __('Item Group'),
                    fieldtype: 'Link',
                    options: 'Item Group',
                    placeholder: __('Select item group'),
                    onchange: function() {
                        item_group = this.value
                        // me.item_group = this.value;
                        // !me.item_group && (me.item_group = me.parent_item_group);
                        // me.filter_items();
                        load_item_data();
                    },
                    get_query: function () {
                        return {
                            query: 'erpnext.selling.page.point_of_sale.point_of_sale.item_group_query',
                            filters: {
                                // pos_profile: doc ? doc.pos_profile : ''
                            }
                        };
                    },
                },
                parent: frm.$component.find('.item-group-field'),
                render_input: true,
            });
            frm.search_field.toggle_label(false);
            frm.item_group_field.toggle_label(false);
        }
        frm.$component.on('click', '.item-wrapper', function(){
            if (!frm.doc.customer) {
                frappe.throw(__("Please Specify Customer before Adding Items"))
            }
            const $item = $(this);
			const item_code = unescape($item.attr('data-item-code'));
			let batch_no = unescape($item.attr('data-batch-no'));
			let serial_no = unescape($item.attr('data-serial-no'));
			let uom = unescape($item.attr('data-uom'));
			const item_name = unescape($item.attr('title'));
			let rate;
            let qty = 0.0;

			// escape(undefined) returns "undefined" then unescape returns "undefined"
			batch_no = batch_no === "undefined" ? undefined : batch_no;
			serial_no = serial_no === "undefined" ? undefined : serial_no;
			uom = uom === "undefined" ? undefined : uom;
            // rate = rate === "undefined" ? undefined : rate;

            frappe.prompt([
                {
                    fieldname: "qty",
                    fieldtype: "Float",
                    label: __("Quantity")
                }
            ],
            (data) => {
                if (data.qty) {
                    qty = data.qty
                }
                frappe.call({
                    method:"erpnext.stock.utils.get_incoming_rate",
                    args:{"args": {
                    "item_code":item_code,
                    "posting_date":frm.doc.posting_date,
                    "posting_time":frm.doc.posting_time,
                    "warehouse":frm.doc.warehouse,
                    "company":frm.doc.company,
                    "qty":qty,
                    "allow_zero_valuation":1
                    }},
                    async:false,
                    callback: function(res){
                        rate = res.message
                    }
                    })
                    add_item(qty,rate,item_code,item_name,batch_no,serial_no,uom)
            },__("Enter the Item Quantity"))
        })

        function add_item(qty,rate,...item){
            console.log(qty,item)
        let is_item = 0
        if (frm.doc.items){
            if (frm.doc.items.length == 1 && !frm.doc.items[0].item_code){
                frm.clear_table("items")
            }
            if (frm.doc.items.length){
                for (let existing_item = 0; existing_item < frm.doc.items.length; existing_item++) {
                    if (item[0] == frm.doc.items[existing_item].item_code){
                        is_item = 1
                        frm.doc.items[existing_item].qty += qty;
                    }
                    frm.refresh_field("items")
                }
            }
        }
        if (!is_item){
            let row = frm.add_child("items");
            row.item_code = item[0]
            row.qty = qty
            row.uom = item[4];
            auto_fill_item_details(frm, item[0],row)
            frm.script_manager.trigger("item_code", row.doctype, row.name)
            frm.refresh_field("items")
        }
        }
    }
});

function auto_fill_item_details(frm,item_name,row){
	frappe.call({
		method: "erpnext.stock.get_item_details.get_item_details",
		args:{
			args: {
			item_code: item_name,
			barcode: row.barcode,
			serial_no: row.serial_no,
			batch_no: row.batch_no,
			set_warehouse: frm.doc.set_warehouse,
			warehouse: row.warehouse,
			customer: frm.doc.customer || frm.doc.party_name,
			quotation_to: frm.doc.quotation_to,
			supplier: frm.doc.supplier,
			currency: frm.doc.currency,
			conversion_rate: frm.doc.conversion_rate,
			price_list: frm.doc.selling_price_list || frm.doc.buying_price_list,
			price_list_currency: frm.doc.price_list_currency,
			plc_conversion_rate: frm.doc.plc_conversion_rate,
			company: frm.doc.company,
			order_type: frm.doc.order_type,
			is_pos: cint(frm.doc.is_pos),
			is_return: cint(frm.doc.is_return),
			is_subcontracted: frm.doc.is_subcontracted,
			ignore_pricing_rule: frm.doc.ignore_pricing_rule,
			doctype: frm.doc.doctype,
			name: frm.doc.name,
			project: row.project || frm.doc.project,
			qty: row.qty || 1,
			net_rate: row.rate,
			stock_qty: row.stock_qty,
			conversion_factor: row.conversion_factor,
			weight_per_unit: row.weight_per_unit,
			uom: row.uom,
			weight_uom: row.weight_uom,
			manufacturer: row.manufacturer,
			stock_uom: row.stock_uom,
			pos_profile: cint(frm.doc.is_pos) ? frm.doc.pos_profile : '',
			cost_center: row.cost_center,
			tax_category: frm.doc.tax_category,
			item_tax_template: row.item_tax_template,
			child_docname: row.name,
			is_old_subcontracting_flow: frm.doc.is_old_subcontracting_flow
			}
		},
		callback:function(r){
			var item = r.message
			row.item_name = item.item_name
			row.description = item.description
			row.uom = item.uom
			row.gst_hsn_code = item.gst_hsn_code
			row.income_account = item.income_account
			row.expense_account = item.expense_account
			row.warehouse = item.warehouse
			row.batch_no = item.batch_no
			frm.refresh_field("items")

		}
	})
}

frappe.ui.form.on("Sales Order Item", {
    item_code: (frm, cdt, cdn) => {
        frm.trigger('set_gross_profit_color')

    }
})