import datetime
import uuid
from fastapi import APIRouter, Depends, HTTPException
from app.dependencies import get_user_from_jwt
from app.database import get_db
from app.models import SubscriptionCreate, SubscriptionUpdate, SubscriptionResponse

router = APIRouter()


def _next_renewal_date(
    renewal_day: int | None,
    from_date: datetime.date | None = None,
) -> datetime.date | None:
    if renewal_day is None:
        return None
    today = from_date or datetime.date.today()
    candidate = today.replace(day=min(renewal_day, 28))
    if candidate <= today:
        # Move to next month
        if today.month == 12:
            candidate = candidate.replace(year=today.year + 1, month=1)
        else:
            candidate = candidate.replace(month=today.month + 1)
    return candidate


def _days_until_renewal(renewal_day: int | None) -> int | None:
    next_date = _next_renewal_date(renewal_day)
    if next_date is None:
        return None
    return (next_date - datetime.date.today()).days


@router.post("/", response_model=SubscriptionResponse)
def create_subscription(
    body: SubscriptionCreate,
    user_id: str = Depends(get_user_from_jwt),
):
    db = get_db()
    row = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "name": body.name,
        "cost_gbp": body.cost_gbp,
        "renewal_day": body.renewal_day,
        "cancel_url": body.cancel_url,
        "is_active": True,
    }
    result = db.table("subscriptions").insert(row).execute()
    data = result.data[0]
    return SubscriptionResponse(**{k: data[k] for k in SubscriptionResponse.model_fields})


@router.get("/", response_model=list[SubscriptionResponse])
def list_subscriptions(user_id: str = Depends(get_user_from_jwt)):
    db = get_db()
    rows = (
        db.table("subscriptions")
        .select("*")
        .eq("user_id", user_id)
        .order("created_at")
        .execute()
        .data or []
    )
    return [SubscriptionResponse(**{k: r[k] for k in SubscriptionResponse.model_fields}) for r in rows]


@router.patch("/{sub_id}", response_model=SubscriptionResponse)
def update_subscription(
    sub_id: str,
    body: SubscriptionUpdate,
    user_id: str = Depends(get_user_from_jwt),
):
    db = get_db()
    existing = db.table("subscriptions").select("id").eq("id", sub_id).eq("user_id", user_id).execute()
    if not existing.data:
        raise HTTPException(status_code=404, detail="Subscription not found")
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    result = db.table("subscriptions").update(updates).eq("id", sub_id).execute()
    data = result.data[0]
    return SubscriptionResponse(**{k: data[k] for k in SubscriptionResponse.model_fields})


@router.delete("/{sub_id}", status_code=204)
def delete_subscription(
    sub_id: str,
    user_id: str = Depends(get_user_from_jwt),
):
    db = get_db()
    existing = db.table("subscriptions").select("id").eq("id", sub_id).eq("user_id", user_id).execute()
    if not existing.data:
        raise HTTPException(status_code=404, detail="Subscription not found")
    db.table("subscriptions").delete().eq("id", sub_id).execute()
