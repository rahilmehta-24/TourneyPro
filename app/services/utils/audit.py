from app.models import db, AuditLog
from app.routes.auth import get_current_user
import json

def log_audit(action_type, target_id=None, target_name=None, reason=None, explanation=None, details=None):
    """
    Logs a sensitive action to the AuditLog.
    """
    current_user = get_current_user()
    if not current_user:
        return
        
    details_str = None
    if details:
        if isinstance(details, dict) or isinstance(details, list):
            details_str = json.dumps(details)
        else:
            details_str = str(details)
            
    log = AuditLog(
        user_id=current_user.id,
        action_type=action_type,
        target_id=target_id,
        target_name=target_name,
        reason=reason,
        explanation=explanation,
        details=details_str
    )
    
    db.session.add(log)
    db.session.commit()
