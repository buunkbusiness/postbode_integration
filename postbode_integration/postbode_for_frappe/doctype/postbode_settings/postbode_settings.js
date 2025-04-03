// Copyright (c) 2025, Buunk Business and contributors
// For license information, please see license.txt

frappe.ui.form.on('Postbode Settings', {
    refresh: function(frm) {
        // Add a warning if customer_code is not set
        if (!frm.doc.customer_code) {
            frm.set_intro(__("Please set your Customer Code by clicking 'Fetch Mailboxes'"), 'yellow');
        }
        
        // Add button to fetch mailboxes
        frm.add_custom_button(__('Fetch Mailboxes'), function() {
            if (!frm.doc.api_key) {
                frappe.msgprint(__('Please enter API Key first'));
                return;
            }
            
            frm.call({
                doc: frm.doc,
                method: 'get_mailboxes',
                freeze: true,
                freeze_message: __('Fetching mailboxes...'),
                callback: function(r) {
                    if (!r.exc && r.message) {
                        if (r.message.length === 0) {
                            frappe.msgprint(__('No mailboxes found for this API key'));
                            return;
                        }
                        
                        // Create a dialog to display mailboxes
                        let mailbox_html = '<div class="mailbox-list">';
                        mailbox_html += '<div class="row font-weight-bold">';
                        mailbox_html += '<div class="col-3">Customer Code</div>';
                        mailbox_html += '<div class="col-5">Name</div>';
                        mailbox_html += '<div class="col-4">Balance</div>';
                        mailbox_html += '</div><hr>';
                        
                        r.message.forEach(function(mailbox) {
                            mailbox_html += `<div class="row mailbox-row" data-code="${mailbox.customer_code}">`;
                            mailbox_html += `<div class="col-3">${mailbox.customer_code}</div>`;
                            mailbox_html += `<div class="col-5">${mailbox.name}</div>`;
                            mailbox_html += `<div class="col-4">${mailbox.balance ? mailbox.balance.current : 0}</div>`;
                            mailbox_html += '</div>';
                        });
                        
                        mailbox_html += '</div>';
                        
                        let d = new frappe.ui.Dialog({
                            title: __('Select Mailbox'),
                            fields: [
                                {
                                    fieldtype: 'HTML',
                                    fieldname: 'mailbox_list',
                                    options: mailbox_html
                                }
                            ],
                            primary_action_label: __('Close'),
                            primary_action: function() {
                                d.hide();
                            }
                        });
                        
                        d.show();
                        
                        // Add click handler to set customer_code
                        d.$wrapper.find('.mailbox-row').click(function() {
                            let customer_code = $(this).data('code');
                            frm.set_value('customer_code', customer_code);
                            d.hide();
                            frappe.show_alert({
                                message: __('Customer Code set to {0}', [customer_code]),
                                indicator: 'green'
                            });
                            
                            // Fetch envelopes for this mailbox
                            frm.save().then(() => {
                                frm.trigger('fetch_envelopes');
                            });
                        });
                        
                        // Add some styling
                        d.$wrapper.find('.mailbox-row').css('cursor', 'pointer');
                        d.$wrapper.find('.mailbox-row').hover(
                            function() { $(this).css('background-color', '#f7fafc'); },
                            function() { $(this).css('background-color', ''); }
                        );
                    }
                }
            });
        }).addClass('btn-primary');
        
        // Add button to fetch envelopes
        if (frm.doc.customer_code) {
            frm.add_custom_button(__('Fetch Envelopes'), function() {
                frm.trigger('fetch_envelopes');
            });
        }
    },
    
    fetch_envelopes: function(frm) {
        frm.call({
            doc: frm.doc,
            method: 'get_available_envelopes',
            freeze: true,
            freeze_message: __('Fetching envelopes...'),
            callback: function(r) {
                if (!r.exc && r.message) {
                    if (r.message.length === 0) {
                        frappe.msgprint(__('No envelopes found for this mailbox'));
                        return;
                    }
                    
                    // Create a dialog to display envelopes
                    let envelope_html = '<div class="envelope-list">';
                    envelope_html += '<div class="row font-weight-bold">';
                    envelope_html += '<div class="col-4">UUID</div>';
                    envelope_html += '<div class="col-8">Name</div>';
                    envelope_html += '</div><hr>';
                    
                    r.message.forEach(function(envelope) {
                        envelope_html += `<div class="row envelope-row" data-uuid="${envelope.uuid}">`;
                        envelope_html += `<div class="col-4">${envelope.uuid}</div>`;
                        envelope_html += `<div class="col-8">${envelope.name}</div>`;
                        envelope_html += '</div>';
                    });
                    
                    envelope_html += '</div>';
                    
                    let d = new frappe.ui.Dialog({
                        title: __('Select Default Envelope'),
                        fields: [
                            {
                                fieldtype: 'HTML',
                                fieldname: 'envelope_list',
                                options: envelope_html
                            }
                        ],
                        primary_action_label: __('Close'),
                        primary_action: function() {
                            d.hide();
                        }
                    });
                    
                    d.show();
                    
                    // Add click handler to set default_envelope_uuid
                    d.$wrapper.find('.envelope-row').click(function() {
                        let uuid = $(this).data('uuid');
                        frm.set_value('default_envelope_uuid', uuid);
                        d.hide();
                        frappe.show_alert({
                            message: __('Default Envelope UUID set to {0}', [uuid]),
                            indicator: 'green'
                        });
                    });
                    
                    // Add some styling
                    d.$wrapper.find('.envelope-row').css('cursor', 'pointer');
                    d.$wrapper.find('.envelope-row').hover(
                        function() { $(this).css('background-color', '#f7fafc'); },
                        function() { $(this).css('background-color', ''); }
                    );
                }
            }
        });
    },
    
    api_key: function(frm) {
        // Clear customer_code when API key changes
        if (frm.doc.customer_code) {
            frm.set_value('customer_code', '');
        }
    },
    
    validate: function(frm) {
        // Check if customer_code is set
        if (!frm.doc.customer_code) {
            frappe.show_alert({
                message: __('Customer Code is required for sending letters'),
                indicator: 'red'
            });
            frappe.validated = false;
        }
    }
});
