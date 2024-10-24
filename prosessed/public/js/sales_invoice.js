frappe.ui.form.on('Sales Invoice', {

    onload: function(frm) {
        toggle_stock_entry_button(frm);
    },
    update_stock: function(frm) {
        toggle_stock_entry_button(frm);
    },
    refresh: function(frm) {
        frm.add_custom_button(__('Add Stock'), function() {

            if (!frm.doc.items || !Array.isArray(frm.doc.items)) {
                frappe.msgprint(__('No items found in the Sales Invoice.'));
                return;
            }

            const items_to_add = frm.doc.items.filter(item => item.stock_qty > item.actual_qty);

            if (items_to_add.length === 0) {
                frappe.msgprint(__('No items available for Stock Entry.'));
                return;
            }

            const dialog = new frappe.ui.Dialog({
                title: __('Create Stock Entry'),
                fields: [
                    {
                        fieldtype: 'Table',
                        fieldname: 'items_table',
                        label: 'Items',
                        description: __('Items with stock_qty > actual_qty'),
                        fields: [
                            {
                                fieldtype: 'Link',
                                fieldname: 'item_code',
                                label: __('Item Code'),
                                options: 'Item', // Link to 'Item' doctype
                                in_list_view: 1,
                                read_only: 0
                            },
                            {
                                fieldtype: 'Float',
                                fieldname: 'stock_qty',
                                label: __('Stock Qty (Available for Transfer)'),
                                in_list_view: 1,
                                read_only: 0
                            },
                            {
                                fieldtype: 'Data',
                                fieldname: 'uom',
                                label: __('UOM'),
                                in_list_view: 1,
                                read_only: 0
                            },
                            {
                                fieldtype: 'Currency',
                                fieldname: 'stock_uom_rate',
                                label: __('Stock UOM Rate'),
                                in_list_view: 1,
                                read_only: 0
                            }
                        ],
                        data: items_to_add.map(item => ({
                            item_code: item.item_code,
                            stock_qty: item.stock_qty - item.actual_qty,
                            uom: item.uom,
                            stock_uom_rate: item.stock_uom_rate
                        })),
                        get_data: function() {
                            return items_to_add.map(item => ({
                                item_code: item.item_code,
                                stock_qty: item.stock_qty - item.actual_qty,
                                uom: item.uom,
                                stock_uom_rate: item.stock_uom_rate
                            }));
                        }
                    }
                ],
                primary_action: function() {
                    const data = dialog.get_values();
                    if (!data || !data.items_table || data.items_table.length === 0) {
                        frappe.msgprint(__('Please fill in all required fields.'));
                        return;
                    }

                    // Prepare the stock entry data
                    const stock_entry_data = {
                        doctype: 'Stock Entry',
                        stock_entry_type: 'Material Receipt',  // Specify the type
                        company: frm.doc.company || 'Your Company Name',
                        posting_date: frappe.datetime.now_date(),
                        posting_time: frappe.datetime.now_time(),
                        items: data.items_table.map(row => ({
                            item_code: row.item_code,
                            qty: row.stock_qty,
                            uom: row.uom,
                            stock_uom: row.uom,
                            basic_rate: row.stock_uom_rate,
                            t_warehouse: frm.doc.set_warehouse, // Specify warehouse as needed
                        }))
                    };

                    // Insert and then submit the stock entry
                    frappe.call({
                        method: 'frappe.client.insert',
                        args: {
                            doc: stock_entry_data
                        },
                        callback: function(r) {
                            if (r.message) {
                                const stock_entry_name = r.message.name;
                                
                                // Now submit the Stock Entry
                                frappe.call({
                                    method: 'frappe.client.submit',
                                    args: {
                                        doc: r.message 
                                    },
                                    callback: function(submit_r) {
                                        frappe.msgprint(__('Stock Entry created and submitted successfully.'));
                                        dialog.hide();
                                        frm.refresh(); 
                                    },
                                    error: function(err) {
                                        console.error(err);
                                        frappe.msgprint(__('An error occurred while submitting the Stock Entry.'));
                                    }
                                });
                            }
                        },
                        error: function(err) {
                            console.error(err);
                            frappe.msgprint(__('An error occurred while creating the Stock Entry.'));
                        }
                    });
                },
                primary_action_label: __('Submit')
            });

            // Show the dialog
            dialog.show();
        });
    }
});

function toggle_stock_entry_button(frm) {
    // Check if update_stock is 0 or 1
    if (frm.doc.update_stock === 0) {
        // Hide the button
        $('button[data-label="Create%20Stock%20Entry"]').hide();
    } else if (frm.doc.update_stock === 1) {
        // Show the button
        $('button[data-label="Create%20Stock%20Entry"]').show();
    }
}

