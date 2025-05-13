import base64
import json
import logging
import os
import requests
import frappe
from frappe import _

# Update API URL to match v2 endpoint
API_BAS_URL = "https://postbode.app/api/v2"
HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json"
}


class Client(object):
    def __init__(self, api_token: str):
        """Instantiate Postbode API client.

        :param api_base_url: API url starting point
        :type api_base_url: str
        :param token: API Token
        :type token: str
        :param mailbox: Mailbox id
        :type mailbox: str
        """

        self.api_base_url = API_BAS_URL
        self.headers = HEADERS

        # prepare header with authorization token.
        # self.headers['X-Authorization'] = api_token

        # setup session object
        self.session = requests.Session()
        self.session.headers = HEADERS
        self.session.headers["X-Authorization"] = api_token

    def hash_document(self, filepath: str) -> str:
        """Base64 encode PDF file.

        :param filepath: The file to use
        :type filepath: str.
        :returns: str of hashed file.
        """
        with open(filepath, "rb") as document:
            encoded_string = base64.b64encode(document.read()).decode("utf-8")
        return encoded_string

    def file_name_check(self, doc_name: str) -> str:
        """Get filename.

        :param doc_name: Full name of document
        :type doc_name: str.
        :returns: str of filename base.

        """
        if doc_name == "":
            self.send_letter.doc_file = os.path.splitext(
                self.send_letter.doc_file)[0]
        else:
            return doc_name

    def get_mailboxes(self):
        """Get all available mailboxes of token."""
        url = "{}/mailbox".format(self.api_base_url)
        response = self.session.get(url)

        if response.status_code == 200:
            return json.loads(response.content)
        else:
            return logging.error(
                "[!] HTTP {} calling {} with headers {}".format(
                    response.status_code, url, self.session.headers
                )
            )

    def get_mailbox(self, mailbox: int):
        """Get mailbox information."""
        url = "{}/mailbox/{}".format(self.api_base_url, mailbox)
        response = self.session.get(url)

        if response.status_code == 200:
            return json.loads(response.content)
        else:
            return logging.error(
                "[!] HTTP {} calling {} with headers {}".format(
                    response.status_code, url, self.session.headers
                )
            )

    def get_letters(self, mailbox: int):
        """Get letters from mailbox."""
        url = "{}/mailbox/{}/letters".format(self.api_base_url, mailbox)
        response = self.session.get(url)

        if response.status_code == 200:
            return json.loads(response.content)
        else:
            return logging.error(
                "[!] HTTP {} calling {} with headers {}".format(
                    response.status_code, url, self.session.headers
                )
            )

    def send_letter(
        self,
        mailbox_id: int,
        doc_name: str,
        doc_file: str,
        envelope_id: int,
        country: str,
        registered: bool,
        color: str,
        printing: str,
        printer: str,
        send: bool,
    ):
        """Send a letter."""

        url = "{}/mailbox/{}/letters".format(self.api_base_url, mailbox_id)

        payload = {
            "documents": [{"name": doc_name, "content": self.hash_document(doc_file)}],
            "envelope_id": envelope_id,
            "country": country,
            "registered": registered,
            "color": color,
            "printing": printing,
            "printer": printer,
            "send": send,
        }

        response = self.session.post(url, json=payload)

        if response.status_code == 200:
            return json.loads(response.content)
        else:
            return logging.error(
                "[!] HTTP {} calling {} with headers {}".format(
                    response.status_code, url, self.session.headers
                )
            )

    def send_letters(
        self,
        mailbox_id: int,
        envelope_id: int,
        country: str,
        registered: bool,
        color: str,
        printing: str,
        printer: str,
        send: bool,
        *letters: str
    ):
        """Send multiple letters at once.

        example:
        letters = ('./file1', './file2')
        client.send_letters(2522, 2, 'NL', False, 'FC', 'simplex', 'inkjet', True, *letters)
        """
        url = "{}/mailbox/{}/letters".format(self.api_base_url, mailbox_id)

        logging.info(">> send_letters docs: {}".format(letters))

        for letter in letters[0]:
            logging.info(">> doc: {}".format(letter))

            self.send_letter(
                mailbox_id,
                self.file_name_check(letter),
                letter,
                envelope_id,
                country,
                registered,
                color,
                printing,
                printer,
                send,
            )


class PostbodeClient:
    """Client for the Postbode API v2 based on the official documentation"""
    
    def __init__(self, api_key, api_url=None):
        self.api_key = api_key
        self.api_url = api_url or API_BAS_URL
        self.headers = {
            "Authorization": f"Bearer {api_key}",  # Changed to Bearer auth for v2 API
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        # Setup session
        self.session = requests.Session()
        self.session.headers = self.headers
    
    def _make_request(self, method, endpoint, data=None):
        """Make a request to the Postbode API"""
        url = f"{self.api_url}/{endpoint}"
        
        try:
            frappe.logger().debug(f"Making {method} request to {url}")
            if data:
                # Log the payload for debugging
                debug_data = data.copy()
                if "documents" in debug_data:
                    for doc in debug_data["documents"]:
                        if "content" in doc:
                            # Ensure proper padding for base64 content
                            doc["content"] = ensure_base64_padding(doc["content"])
                            
                            # Validate that the content is base64-encoded and starts with '%PDF'
                            decoded_content = base64.b64decode(doc["content"])
                            if not decoded_content.startswith(b"%PDF"):
                                frappe.throw(_("Document content is not a valid PDF."))
                            doc["content"] = f"[BASE64 ENCODED CONTENT, LENGTH: {len(doc['content'])}]"
                    frappe.logger().debug(f"Request payload: {json.dumps(debug_data, indent=2)}")
            
            if method.lower() == "get":
                response = self.session.get(url)
            elif method.lower() == "post":
                response = self.session.post(url, json=data)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            # Check response status
            if response.status_code >= 200 and response.status_code < 300:
                try:
                    return response.json()
                except json.JSONDecodeError:
                    frappe.logger().error(f"Non-JSON response: {response.text}")
                    return {"status": "success", "message": "Operation completed successfully"}
            else:
                error_msg = f"HTTP {response.status_code} calling {url}"
                frappe.logger().error(f"{error_msg}\nResponse: {response.text}")
                try:
                    error_json = response.json()
                    raise Exception(error_json.get("message", error_msg))
                except json.JSONDecodeError:
                    raise Exception(error_msg)
        except requests.exceptions.RequestException as e:
            frappe.logger().error(f"Request error: {str(e)}")
            raise
    
    def get_mailboxes(self):
        """Get all available mailboxes for the API key"""
        # Updated to use v2 endpoint
        return self._make_request("get", "mailboxes")
    
    def get_mailbox(self, customer_code):
        """Get details of a specific mailbox"""
        # Updated to use v2 endpoint
        return self._make_request("get", f"mailbox/{customer_code}")
    
    def send_letter(self, data):
        """Send a letter via Postbode API (called 'postal' in v2)"""
        # Updated to use v2 endpoint
        return self._make_request("post", "postal", data)
    
    def check_letter_status(self, postal_uuid):
        """Check the status of a letter by its UUID"""
        # Updated to use v2 endpoint
        return self._make_request("get", f"postal/{postal_uuid}")
    
    def get_letter_logs(self, postal_uuid):
        """Get logs for a letter"""
        # Updated to use v2 endpoint
        return self._make_request("get", f"postal/{postal_uuid}/logs")
    
    def perform_letter_action(self, postal_uuid, action):
        """Perform an action on a letter (like cancel)"""
        # Updated to use v2 endpoint and match the expected payload
        return self._make_request("post", f"postal/{postal_uuid}/status", {"action": action})
    
    def cancel_letter(self, postal_uuid):
        """Cancel a letter that hasn't been sent yet"""
        return self.perform_letter_action(postal_uuid, "cancel")
    
    def prepare_letter_payload(self, letter_doc):
        """
        Prepare the payload for sending a letter according to Postbode API v2
        """
        # Convert country name to country code
        country_code = "NL"  # Default to Netherlands
        if hasattr(letter_doc, "recipient_country"):
            country = letter_doc.recipient_country
            # Handle common country names
            country_map = {
                "netherlands": "NL",
                "nederland": "NL",
                "belgium": "BE",
                "belgië": "BE",
                "germany": "DE",
                "duitsland": "DE",
                "france": "FR",
                "frankrijk": "FR",
                "united kingdom": "GB",
                "verenigd koninkrijk": "GB",
                "uk": "GB",
            }
            if country.lower() in country_map:
                country_code = country_map[country.lower()]
            elif len(country) == 2:
                country_code = country.upper()
        
        # Get mailbox code from settings
        settings = frappe.get_single("Postbode Settings")
        mailbox_code = settings.customer_code
        
        if not mailbox_code:
            frappe.throw(_("Customer Code is required. Please set it in Postbode Settings."))
        
        # Determine printing options based on letter fields
        color_printing = "COLOR" if getattr(letter_doc, "color", False) else "BLACK"
        plex = "DUPLEX" if getattr(letter_doc, "double_sided", False) else "SIMPLEX"
        
        # Create recipient address object
        recipient_address = {
            "name": getattr(letter_doc, "recipient_name", ""),
            "street": getattr(letter_doc, "recipient_address", ""),
            "postal_code": getattr(letter_doc, "recipient_postal_code", ""),
            "city": getattr(letter_doc, "recipient_city", ""),
            "country": country_code,
            "blanco_page": False  # Default to False
        }
        
        # Set up the payload according to v2 API documentation
        payload = {
            "mailbox": mailbox_code,
            "customer_reference": f"{letter_doc.reference_doctype}:{letter_doc.reference_name}" if hasattr(letter_doc, "reference_doctype") and hasattr(letter_doc, "reference_name") else None,
            "type": "outbound_letter",
            "envelope": settings.default_envelope_uuid,  # From settings
            "shipping": "NL_FAST",  # Default shipping option
            "printing": color_printing,
            "plex": plex,
            "paper_type": "A4_90",  # Default paper type
            "metadata": {
                "invoice_id": getattr(letter_doc, "invoice_id", None),
                "customer_id": getattr(letter_doc, "customer_id", None)
            },
            "tags": getattr(letter_doc, "tags", []),  # Optional tags
            "send": True,  # Actually send the letter
            "cover_address": recipient_address,
            "documents": []  # Will be filled below
        }
        
        # Add document to payload with base64 content
        if not letter_doc.base64_content:
            frappe.throw(_("Base64 content is missing. Please regenerate the letter content."))
        
        # Validate that the base64 content decodes to a valid PDF
        try:
            decoded_content = base64.b64decode(letter_doc.base64_content)
            if not decoded_content.startswith(b"%PDF"):
                frappe.throw(_("The base64 content is not a valid PDF. Please check the attachment."))
        except Exception as e:
            frappe.log_error(
                title=_("Base64 Validation Error"),
                message=f"Error validating base64 content: {str(e)}"
            )
            frappe.throw(_("Error validating base64 content: {0}").format(str(e)))
        
        payload["documents"].append({
            "filename": f"Letter-{letter_doc.name}.pdf" if letter_doc.letter_type == "HTML Content" else letter_doc.attachment,
            "content": letter_doc.base64_content
        })
        
        # Log the complete payload for debugging
        debug_payload = payload.copy()
        if "documents" in debug_payload:
            for doc in debug_payload["documents"]:
                if "content" in doc:
                    doc["content"] = f"[BASE64 ENCODED CONTENT, LENGTH: {len(doc['content'])}]"
        
        frappe.logger().debug(f"Prepared payload: {json.dumps(debug_payload, indent=2)}")
        
        return payload