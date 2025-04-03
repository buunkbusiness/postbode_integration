import frappe
from frappe import _
from frappe.model.document import Document
from postbode_integration.client import PostbodeClient, API_BAS_URL

class PostbodeSettings(Document):
    def validate(self):
        if not self.api_key:
            frappe.throw(_("API Key is required for Postbode integration"))
        
        if not self.customer_code:
            frappe.msgprint(
                _("Customer Code is required for sending letters. Click 'Fetch Mailboxes' to get your available mailboxes."),
                indicator='orange',
                alert=True
            )
            
        if not self.default_envelope_uuid:
            frappe.msgprint(
                _("Default Envelope UUID is required for sending letters. You can find this in your Postbode dashboard."),
                indicator='orange',
                alert=True
            )
    
    def get_postbode_client(self):
        """Returns an instance of the PostbodeClient"""
        return PostbodeClient(api_key=self.api_key, api_url=API_BAS_URL)
    
    @frappe.whitelist()
    def get_mailboxes(self):
        """Get available mailboxes from Postbode API"""
        if not self.api_key:
            frappe.throw(_("API Key is required to get mailboxes"))
            
        client = self.get_postbode_client()
        mailboxes = client.get_mailboxes()
        
        return mailboxes
        
    @frappe.whitelist()
    def get_available_envelopes(self):
        """Get available envelopes for the selected mailbox"""
        if not self.api_key:
            frappe.throw(_("API Key is required to get envelopes"))
            
        if not self.customer_code:
            frappe.throw(_("Customer Code is required to get envelopes"))
            
        client = self.get_postbode_client()
        return client._make_request("get", f"mailbox/{self.customer_code}/envelopes")
