import frappe
from frappe import _

def setup_postbode_client():
    """
    Make sure the PostbodeSettings class has the get_postbode_client method
    This ensures compatibility regardless of import path issues
    """
    from postbode_integration.client import PostbodeClient, API_BAS_URL
    
    # Get the current PostbodeSettings class
    try:
        PostbodeSettings = frappe.get_doc("DocType", "Postbode Settings").get_controller_class()
        
        # Check if the method already exists
        if not hasattr(PostbodeSettings, "get_postbode_client"):
            # Define the method and attach it to the class
            def get_postbode_client(self):
                """Returns an instance of the PostbodeClient"""
                return PostbodeClient(api_key=self.api_key, api_url=API_BAS_URL)
            
            # Add the method to the class
            PostbodeSettings.get_postbode_client = get_postbode_client
            
            frappe.log_error(
                title=_("Postbode Setup"),
                message="Added get_postbode_client method to PostbodeSettings class"
            )
    except Exception as e:
        frappe.log_error(
            title=_("Postbode Setup Error"),
            message=f"Error setting up Postbode client: {str(e)}"
        )
