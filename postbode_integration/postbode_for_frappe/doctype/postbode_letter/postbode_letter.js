frappe.ui.form.on('Postbode Letter', {
    refresh: function(frm) {
        // Add send button if draft or failed
        if (frm.doc.status === 'Draft' || frm.doc.status === 'Failed') {
            frm.add_custom_button(__('Send Letter'), function() {
                frappe.confirm(
                    __('Are you sure you want to send this letter via Postbode?'),
                    function() {
                        frm.call({
                            doc: frm.doc,
                            method: 'send_letter',
                            freeze: true,
                            freeze_message: __('Sending letter...'),
                            callback: function(r) {
                                if (!r.exc) {
                                    frappe.show_alert({
                                        message: __('Letter sent successfully'),
                                        indicator: 'green'
                                    });
                                    frm.refresh();
                                }
                            }
                        });
                    }
                );
            }).addClass('btn-primary');
        }
        
        // Add check status button if sent
        if (frm.doc.status !== 'Draft' && frm.doc.postbode_id) {
            frm.add_custom_button(__('Check Status'), function() {
                frm.call({
                    doc: frm.doc,
                    method: 'check_status',
                    freeze: true,
                    freeze_message: __('Checking letter status...'),
                    callback: function(r) {
                        if (!r.exc) {
                            frappe.show_alert({
                                message: __('Status updated'),
                                indicator: 'green'
                            });
                            frm.refresh();
                        }
                    }
                });
            });
        }
        
        // Add cancel button if letter can be cancelled
        if (['Draft', 'Processing'].includes(frm.doc.status) && frm.doc.postbode_id) {
            frm.add_custom_button(__('Cancel Letter'), function() {
                frappe.confirm(
                    __('Are you sure you want to cancel this letter?'),
                    function() {
                        frm.call({
                            doc: frm.doc,
                            method: 'cancel_letter',
                            freeze: true,
                            freeze_message: __('Cancelling letter...'),
                            callback: function(r) {
                                if (!r.exc) {
                                    frappe.show_alert({
                                        message: __('Letter cancelled'),
                                        indicator: 'green'
                                    });
                                    frm.refresh();
                                }
                            }
                        });
                    }
                );
            }).addClass('btn-danger');
        }
        
        // Add logs button
        frm.add_custom_button(__('View Logs'), function() {
            frappe.set_route('List', 'Postbode Letter Log', {letter: frm.doc.name});
        });
        
        // Add preview button for HTML content letters
        if (frm.doc.letter_type === 'HTML Content' && frm.doc.letter_content) {
            frm.add_custom_button(__('Preview PDF'), function() {
                frm.call({
                    doc: frm.doc,
                    method: 'generate_pdf_preview',
                    freeze: true,
                    freeze_message: __('Generating PDF preview...'),
                    callback: function(r) {
                        if (!r.exc && r.message && r.message.status === 'success') {
                            // Open the PDF in a new tab
                            window.open(
                                frappe.urllib.get_full_url(r.message.file_url),
                                '_blank'
                            );
                        }
                    }
                });
            });
        }
    },
    
    letter_type: function(frm) {
        // Toggle required fields based on letter type
        frm.toggle_reqd('letter_content', frm.doc.letter_type === 'HTML Content');
        frm.toggle_reqd('attachment', frm.doc.letter_type === 'PDF Attachment');
    },
    
    use_default_sender: function(frm) {
        if (frm.doc.use_default_sender) {
            frappe.call({
                method: 'frappe.client.get_value',
                args: {
                    doctype: 'Postbode Settings',
                    fieldname: [
                        'default_sender_name',
                        'default_sender_company',
                        'default_sender_address',
                        'default_sender_postal_code',
                        'default_sender_city',
                        'default_sender_country'
                    ]
                },
                callback: function(r) {
                    if (r.message) {
                        frm.set_value('sender_name', r.message.default_sender_name);
                        frm.set_value('sender_company', r.message.default_sender_company);
                        frm.set_value('sender_address', r.message.default_sender_address);
                        frm.set_value('sender_postal_code', r.message.default_sender_postal_code);
                        frm.set_value('sender_city', r.message.default_sender_city);
                        frm.set_value('sender_country', r.message.default_sender_country);
                    }
                }
            });
        }
    }
});
