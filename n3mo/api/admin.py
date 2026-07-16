import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from n3mo.api.auth import get_current_user_from_token
from n3mo.saas_db import (
    get_all_users_with_subscriptions, 
    update_subscription,
    get_discount_codes,
    create_discount_code,
    delete_discount_code
)

logger = logging.getLogger("n3mo.api.admin")
router = APIRouter()

def require_admin(user: dict = Depends(get_current_user_from_token)):
    if not user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin privileges required")
    return user

class SubscriptionUpdateRequest(BaseModel):
    plan_type: str
    status: str

class DiscountCodeCreateRequest(BaseModel):
    code: str
    discount_percentage: int
    max_uses: int = -1
    expires_at: datetime | None = None

@router.get("/users")
def get_users(admin_user: dict = Depends(require_admin)):
    users = get_all_users_with_subscriptions()
    return {"users": users}

@router.put("/users/{user_id}/subscription")
def update_user_sub(user_id: str, req: SubscriptionUpdateRequest, admin_user: dict = Depends(require_admin)):
    success = update_subscription(user_id, "user", req.plan_type, req.status)
    if success:
        return {"status": "success"}
    else:
        raise HTTPException(status_code=500, detail="Failed to update subscription")

@router.get("/discounts")
def list_discounts(admin_user: dict = Depends(require_admin)):
    codes = get_discount_codes()
    return {"discounts": codes}

@router.post("/discounts")
def new_discount(req: DiscountCodeCreateRequest, admin_user: dict = Depends(require_admin)):
    success = create_discount_code(req.code, req.discount_percentage, req.max_uses, req.expires_at)
    if success:
        return {"status": "success"}
    else:
        raise HTTPException(status_code=500, detail="Failed to create discount code")

@router.delete("/discounts/{code}")
def remove_discount(code: str, admin_user: dict = Depends(require_admin)):
    success = delete_discount_code(code)
    if success:
        return {"status": "success"}
    else:
        raise HTTPException(status_code=500, detail="Failed to delete discount code")
