from app.domain.models import db, AuditLog
from app.web.controllers.auth import get_current_user
import json

def log_audit(action_type, target_id=None, target_name=None, reason=None, explanation=None, details=None, user_id=None):
    """
    Logs a sensitive action to the AuditLog for auditing and compliance (SEC-069, SEC-093).
    """
    if user_id is None:
        current_user = get_current_user()
        if current_user:
            user_id = current_user.id
        else:
            try:
                from flask_jwt_extended import get_jwt_identity
                jwt_id = get_jwt_identity()
                if jwt_id and str(jwt_id).isdigit():
                    user_id = int(jwt_id)
            except Exception:
                pass

    if not user_id:
        return
        
    details_str = None
    if details:
        if isinstance(details, (dict, list)):
            details_str = json.dumps(details)
        else:
            details_str = str(details)
            
    log = AuditLog(
        user_id=user_id,
        action_type=action_type,
        target_id=target_id,
        target_name=target_name,
        reason=reason or "System Action",
        explanation=explanation,
        details=details_str
    )
    
    db.session.add(log)
    db.session.commit()
