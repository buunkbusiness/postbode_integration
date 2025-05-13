import frappe
from frappe import _
from frappe.utils import cstr
import json

@frappe.whitelist()
def send_letter(letter_id=None, doctype=None, docname=None, recipients=None, content=None, pdf_attachment=None):
    """
    Send a letter via Postbode API
    
    Args:
        letter_id: Existing Postbode Letter ID to send
        doctype, docname: Reference document to create a letter from
        recipients: JSON string of recipient information
        content: HTML content for the letter
        pdf_attachment: File name of an attachment to send
    
    Returns:
        Dict with status and message
    """
    try:
        # Validate inputs
        if not letter_id and not (doctype and docname):
            frappe.throw(_("Either letter_id or doctype and docname must be provided"))
        
        # Log the inputs for debugging
        frappe.logger().debug(f"send_letter called with letter_id={letter_id}, doctype={doctype}, docname={docname}")
        
        # Case 1: Sending an existing letter
        if letter_id:
            letter = frappe.get_doc("Postbode Letter", letter_id)
            response = letter.send_letter()
            
            # Log the response for debugging
            frappe.logger().debug(f"Letter sent successfully: {response}")
            
            return {
                "status": "success",
                "message": _("Letter sent successfully"),
                "letter_id": letter.name,
                "postbode_id": letter.postbode_id
            }
        
        # Case 2: Creating and sending a new letter
        elif doctype and docname:
            # Validate permissions on the source document
            if not frappe.has_permission(doctype, "read", docname):
                frappe.throw(_("No permission to access {0} {1}").format(doctype, docname))
            
            # Create letter from source document
            letter = frappe.new_doc("Postbode Letter")
            letter.reference_doctype = doctype
            letter.reference_name = docname
            
            # Set recipient if provided
            if recipients:
                try:
                    recipient_data = json.loads(recipients)
                    letter.recipient_name = recipient_data.get("name")
                    letter.recipient_company = recipient_data.get("company", "")
                    letter.recipient_address = recipient_data.get("address")
                    letter.recipient_postal_code = recipient_data.get("postal_code")
                    letter.recipient_city = recipient_data.get("city")
                    letter.recipient_country = recipient_data.get("country")
                except Exception as e:
                    frappe.throw(_("Invalid recipient data: {0}").format(str(e)))
            
            # Set content
            if content:
                letter.letter_type = "HTML Content"
                letter.letter_content = content
            elif pdf_attachment:
                letter.letter_type = "PDF Attachment"
                letter.attachment = pdf_attachment
            
            letter.insert()
            
            # Send the letter
            response = letter.send_letter()
            
            # Log the response for debugging
            frappe.logger().debug(f"Letter sent successfully: {response}")
            
            return {
                "status": "success",
                "message": _("Letter created and sent successfully"),
                "letter_id": letter.name,
                "postbode_id": letter.postbode_id
            }
        
        else:
            frappe.throw(_("Either letter_id or doctype and docname must be provided"))
            
    except Exception as e:
        frappe.log_error(
            title=_("Postbode Letter API Error"),
            message=str(e)
        )
        return {
            "status": "error",
            "message": str(e)
        }

@frappe.whitelist()
def check_letter_status(letter_id):
    """
    Check the status of a letter
    
    Args:
        letter_id: Postbode Letter ID
    
    Returns:
        Dict with updated status information
    """
    try:
        letter = frappe.get_doc("Postbode Letter", letter_id)
        response = letter.check_status()
        
        return {
            "status": "success",
            "letter_status": letter.status,
            "message": _("Status updated successfully"),
            "details": response
        }
    except Exception as e:
        frappe.log_error(
            title=_("Postbode Status Check Error"),
            message=str(e)
        )
        return {
            "status": "error",
            "message": str(e)
        }

@frappe.whitelist()
def get_letter_preview(letter_id):
    """
    Get a preview URL for a letter
    
    Args:
        letter_id: Postbode Letter ID
    
    Returns:
        Dict with preview URL if available
    """
    try:
        letter = frappe.get_doc("Postbode Letter", letter_id)
        
        if not letter.postbode_id:
            return {
                "status": "error",
                "message": _("Letter has not been sent to Postbode yet")
            }
        
        settings = frappe.get_single("Postbode Settings")
        client = settings.get_postbode_client()
        
        response = client.get_letter_preview(letter.postbode_id)
        
        return {
            "status": "success",
            "preview_url": response.get("preview_url"),
            "message": _("Preview URL generated")
        }
    except Exception as e:
        frappe.log_error(
            title=_("Postbode Preview Error"),
            message=str(e)
        )
        return {
            "status": "error",
            "message": str(e)
        }

@frappe.whitelist()
def get_available_mailboxes(api_key=None):
    """
    Get available mailboxes for an API key
    
    Args:
        api_key: Optional Postbode API key (if not provided, gets from settings)
    
    Returns:
        List of available mailboxes
    """
    try:
        if not api_key:
            settings = frappe.get_single("Postbode Settings")
            api_key = settings.api_key
        
        if not api_key:
            frappe.throw(_("API Key is required to get mailboxes"))
        
        from postbode_integration.client import PostbodeClient, API_BAS_URL
        client = PostbodeClient(api_key=api_key, api_url=API_BAS_URL)
        
        return client.get_mailboxes()
    except Exception as e:
        frappe.log_error(
            title=_("Postbode Mailbox Fetch Error"),
            message=str(e)
        )
        return {
            "status": "error",
            "message": str(e)
        }
