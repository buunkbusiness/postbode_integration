import frappe
from frappe import _
from frappe.utils import now_datetime, add_days

def update_letter_status():
    """
    Update status of pending letters
    This function is meant to be scheduled to run periodically
    """
    # Get letters that were sent in the last 30 days and are not in a final state
    date_30_days_ago = add_days(now_datetime(), -30)
    
    # Get letters that are not in a final state (adjust status list as needed)
    non_final_statuses = ["Pending", "Processing", "Sent"]
    
    letters = frappe.get_all(
        "Postbode Letter",
        filters={
            "status": ["in", non_final_statuses],
            "postbode_id": ["is", "set"],
            "creation": [">=", date_30_days_ago]
        },
        fields=["name", "postbode_id", "status"]
    )
    
    updated_count = 0
    
    for letter in letters:
        try:
            doc = frappe.get_doc("Postbode Letter", letter.name)
            response = doc.check_status()
            
            if doc.status != letter.status:
                updated_count += 1
                frappe.db.commit()
        except Exception as e:
            frappe.log_error(
                title=_("Postbode Status Update Error"),
                message=f"Error updating status for letter {letter.name}: {str(e)}"
            )
    
    return updated_count
