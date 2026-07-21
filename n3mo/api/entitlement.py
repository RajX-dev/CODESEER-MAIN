from fastapi import HTTPException, Depends
from n3mo.api.auth import get_current_user_from_token
from n3mo.saas_db import get_subscription

def require_active_subscription(current_user: dict = Depends(get_current_user_from_token)) -> dict:
    """Dependency that ensures the user has an active or trialing subscription."""
    user_id = current_user["user_id"]
    sub = get_subscription(user_id, "user")
    
    if sub.get("status") not in ("active", "trialing"):
        raise HTTPException(
            status_code=402,
            detail="Payment Required: An active subscription or trial is required to access this feature."
        )
    return current_user
