import frappe
from frappe import _
from frappe.model.document import Document
import json
import base64

def ensure_base64_padding(base64_string):
    """Ensure the base64 string has proper padding."""
    missing_padding = len(base64_string) % 4
    if missing_padding:
        base64_string += "=" * (4 - missing_padding)
    return base64_string

class PostbodeLetter(Document):
    def validate(self):
        self.validate_required_fields()
        self.generate_base64_content()
    
    def validate_required_fields(self):
        """Validate that all required fields are filled"""
        required_fields = [
            "recipient_name", "recipient_address", "recipient_postal_code", 
            "recipient_city", "recipient_country", "sender_name", 
            "sender_address", "sender_postal_code", "sender_city", "sender_country"
        ]
        
        for field in required_fields:
            if not self.get(field):
                frappe.throw(_("{0} is required").format(_(frappe.get_meta("Postbode Letter").get_field(field).label)))
        
        if self.letter_type == "HTML Content" and not self.letter_content:
            frappe.throw(_("Letter Content is required for HTML Content letters"))
        elif self.letter_type == "PDF Attachment" and not self.attachment:
            frappe.throw(_("Attachment is required for PDF Attachment letters"))
    
    def generate_base64_content(self):
        """Generate and store base64 content for the letter."""
        if self.letter_type == "HTML Content":
            # Generate PDF from HTML content
            html_content = self.letter_content
            if not html_content.strip().lower().startswith("<!doctype") and not html_content.strip().lower().startswith("<html"):
                html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Letter {self.name}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 2cm; }}
        .header {{ margin-bottom: 2cm; }}
        .recipient, .sender {{ margin-bottom: 1cm; }}
        .content {{ line-height: 1.5; }}
    </style>
</head>
<body>
    <div class="header">
        <div class="sender">
            {self.sender_company}<br>
            {self.sender_name}<br>
            {self.sender_address}<br>
            {self.sender_postal_code} {self.sender_city}<br>
            {self.sender_country}
        </div>
        <div class="recipient">
            {self.recipient_company}<br>
            {self.recipient_name}<br>
            {self.recipient_address}<br>
            {self.recipient_postal_code} {self.recipient_city}<br>
            {self.recipient_country}
        </div>
    </div>
    <div class="content">
        {self.letter_content}
    </div>
</body>
</html>
"""
            try:
                from frappe.utils.pdf import get_pdf
                pdf_content = get_pdf(html_content)
                
                # Validate that the generated PDF starts with the '%PDF' header
                if not pdf_content.startswith(b"%PDF"):
                    frappe.throw(_("Generated PDF content is invalid."))
                
                base64_content = base64.b64encode(pdf_content).decode("utf-8")
                self.base64_content = ensure_base64_padding(base64_content)
                frappe.logger().debug(f"Generated base64 content for HTML letter: {self.base64_content[:50]}...")  # Log first 50 characters
            except Exception as e:
                frappe.log_error(
                    title=_("PDF Generation Error"),
                    message=f"Error generating PDF: {str(e)}"
                )
                frappe.throw(_("Error generating PDF: {0}").format(str(e)))
        elif self.letter_type == "PDF Attachment" and self.attachment:
            try:
                file_doc = frappe.get_doc("File", {"file_url": self.attachment})
                file_path = file_doc.get_full_path()
                
                # Validate that the file is a PDF
                if not file_doc.file_name.lower().endswith(".pdf"):
                    frappe.throw(_("The attached file must be a PDF."))
                
                # Read and encode the PDF file as base64
                with open(file_path, "rb") as f:
                    pdf_content = f.read()
                    
                    # Validate that the file starts with the '%PDF' header
                    if not pdf_content.startswith(b"%PDF"):
                        frappe.throw(_("The attached file is not a valid PDF."))
                    
                    base64_content = base64.b64encode(pdf_content).decode("utf-8")
                    self.base64_content = ensure_base64_padding(base64_content)
                    frappe.logger().debug(f"Generated base64 content for PDF attachment: {self.base64_content[:50]}...")  # Log first 50 characters
                
                # Log the size of the encoded content for debugging
                frappe.logger().debug(f"Base64 content generated for {self.name}, size: {len(self.base64_content)}")
            except Exception as e:
                frappe.log_error(
                    title=_("PDF Attachment Error"),
                    message=f"Error processing PDF attachment: {str(e)}"
                )
                frappe.throw(_("Error processing PDF attachment: {0}").format(str(e)))
    
    @frappe.whitelist()
    def send_letter(self):
        """Send the letter via Postbode API"""
        try:
            if self.postbode_id:
                frappe.throw(_("This letter has already been sent"))
            
            settings = frappe.get_single("Postbode Settings")
            
            # Check if API key and customer_code are set
            if not settings.api_key:
                frappe.throw(_("API Key is required. Please set it in Postbode Settings before sending letters."))
                
            if not settings.customer_code:
                frappe.throw(_("Customer Code is required. Please set it in Postbode Settings before sending letters."))
                
            if not settings.default_envelope_uuid:
                frappe.throw(_("Default Envelope UUID is required. Please set it in Postbode Settings before sending letters."))
            
            # Fallback if get_postbode_client is not available
            try:
                client = settings.get_postbode_client()
            except AttributeError:
                from postbode_integration.client import PostbodeClient, API_BAS_URL
                client = PostbodeClient(api_key=settings.api_key, api_url=API_BAS_URL)
                
                # Log this fallback for debugging
                frappe.log_error(
                    title=_("Postbode Client Fallback"),
                    message="Using fallback client creation method"
                )
            
            # Create a test letter first if in test mode
            if settings.environment == "Test":
                frappe.logger().debug("Creating test letter first in test environment")
                # Add test indicator to content if it's HTML
                if self.letter_type == "HTML Content":
                    original_content = self.letter_content
                    self.letter_content = f"<div style='color:red; text-align:center; margin:20px;'>[TEST LETTER]</div>{original_content}"
            
            # Prepare payload
            try:
                payload = client.prepare_letter_payload(self)
                
                # Log the payload for debugging
                frappe.logger().debug(f"Payload before sending: {json.dumps(payload, indent=2)}")
                
                # Send letter
                response = client.send_letter(payload)
                
                # Update document with postbode_id and status
                self.postbode_id = response.get("uuid")  # Changed from id to uuid
                
                # Map Postbode status to internal status
                status_obj = response.get("status", {})
                postbode_status = status_obj.get("code", 1)  # Default to 1 (concept)
                self.status = self._map_postbode_status(postbode_status)
                
                self.save()
                
                # Add log entry
                self.add_log("Letter sent", json.dumps(response))
                
                # Restore original content if modified for testing
                if settings.environment == "Test" and 'original_content' in locals():
                    self.letter_content = original_content
                    self.save()
                
                return response
            except Exception as e:
                frappe.logger().error(f"Error in letter payload or sending: {str(e)}")
                # Re-raise with more helpful message
                raise Exception(f"Error sending letter: {str(e)}")
        except Exception as e:
            # Log the error
            frappe.log_error(
                title=_("Postbode Letter Sending Error"),
                message=f"Error sending letter: {str(e)}"
            )
            # Re-raise the exception
            raise
    
    @frappe.whitelist()
    def check_status(self):
        """Check the status of the letter"""
        if not self.postbode_id:
            frappe.throw(_("This letter has not been sent yet"))
        
        settings = frappe.get_single("Postbode Settings")
        
        # Fallback if get_postbode_client is not available
        try:
            client = settings.get_postbode_client()
        except AttributeError:
            from postbode_integration.client import PostbodeClient, API_BAS_URL
            client = PostbodeClient(api_key=settings.api_key, api_url=API_BAS_URL)
        
        response = client.check_letter_status(self.postbode_id)
        
        # Update status - structure changed in v2 API
        status_obj = response.get("status", {})
        postbode_status = status_obj.get("code", 0)
        
        if postbode_status:
            new_status = self._map_postbode_status(postbode_status)
            if self.status != new_status:
                old_status = self.status
                self.status = new_status
                self.save()
                self.add_log(f"Status changed from {old_status} to {new_status}", json.dumps(response))
        
        return response

    @frappe.whitelist()
    def cancel_letter(self):
        """Cancel a letter that hasn't been sent yet"""
        if not self.postbode_id:
            frappe.throw(_("This letter has not been sent yet"))
        
        settings = frappe.get_single("Postbode Settings")
        
        try:
            client = settings.get_postbode_client()
        except AttributeError:
            from postbode_integration.client import PostbodeClient, API_BAS_URL
            client = PostbodeClient(api_key=settings.api_key, api_url=API_BAS_URL)
        
        response = client.cancel_letter(self.postbode_id)
        
        # Update status
        self.status = "Cancelled"
        self.save()
        
        # Add log entry
        self.add_log("Letter cancelled", json.dumps(response) if response else "")
        
        return {"status": "success", "message": _("Letter cancelled")}
    
    def _map_postbode_status(self, postbode_status):
        """Map Postbode status to internal status"""
        # Status codes have changed in v2 API
        status_map = {
            1: "Draft",        # concept
            15: "Processing",  # processing
            16: "Sent",        # sent
            20: "Delivered",   # delivered
            500: "Failed",     # failed
            600: "Cancelled"   # cancelled
        }
        return status_map.get(postbode_status, "Unknown")
    
    def add_log(self, action, data=None):
        """Add a log entry for the letter"""
        log = frappe.get_doc({
            "doctype": "Postbode Letter Log",
            "letter": self.name,
            "action": action,
            "data": data or "",
            "timestamp": frappe.utils.now()
        })
        log.insert(ignore_permissions=True)
        return log

    @frappe.whitelist()
    def generate_pdf_preview(self):
        """Generate a PDF preview of the letter with recipient and sender details"""
        try:
            if self.letter_type != "HTML Content":
                frappe.throw(_("PDF preview is only available for HTML content letters"))
            
            # Prepare the letter content with recipient and sender details
            html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Letter {self.name}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 2cm; }}
        .header {{ margin-bottom: 2cm; }}
        .recipient, .sender {{ margin-bottom: 1cm; }}
        .content {{ line-height: 1.5; }}
    </style>
</head>
<body>
    <div class="header">
        <div class="sender">
            {self.sender_company}<br>
            {self.sender_name}<br>
            {self.sender_address}<br>
            {self.sender_postal_code} {self.sender_city}<br>
            {self.sender_country}
        </div>
        <div class="recipient">
            {self.recipient_company}<br>
            {self.recipient_name}<br>
            {self.recipient_address}<br>
            {self.recipient_postal_code} {self.recipient_city}<br>
            {self.recipient_country}
        </div>
    </div>
    <div class="content">
        {self.letter_content}
    </div>
</body>
</html>
"""
            # Generate PDF
            from frappe.utils.pdf import get_pdf
            pdf_content = get_pdf(html_content)
            
            # Generate a temporary file for the preview
            from frappe.utils.file_manager import save_file
            filename = f"Preview-{self.name}.pdf"
            
            # Save the file and attach it to the current document
            file_doc = save_file(
                filename,
                pdf_content,
                "Postbode Letter",
                self.name,
                is_private=1
            )
            
            return {
                "status": "success",
                "message": _("PDF preview generated"),
                "file_url": file_doc.file_url
            }
            
        except Exception as e:
            frappe.log_error(
                title=_("PDF Preview Generation Error"),
                message=f"Error generating PDF preview: {str(e)}"
            )
            return {
                "status": "error",
                "message": str(e)
            }
