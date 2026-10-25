"""Plan resolution and free-tier limits.

Free tier: every feature, capped at FREE_PROCESS_LIMIT processes.
Paid plans ('monthly' / 'yearly') lift the cap. A user's effective plan is
always derived from the `customers` table (written by the Stripe webhook),
so subscribing after registration upgrades automatically on the next check —
and a lapsed subscription falls back to free without deleting anything.
"""

FREE_PROCESS_LIMIT = 2
PAID_PLANS = ("monthly", "yearly")


def is_paid(plan: str | None) -> bool:
    return plan in PAID_PLANS


def can_add_process(plan: str | None, current_count: int) -> bool:
    """Whether this account may create one more process.

    Existing processes are never deleted or blocked by the cap — it only
    gates the creation of new ones.
    """
    if is_paid(plan):
        return True
    return current_count < FREE_PROCESS_LIMIT


def plan_from_customer_row(row: dict | None) -> str:
    """Derive the effective plan from a `customers` row (or its absence)."""
    if not row or row.get("status") != "active":
        return "free"
    plan = row.get("plan")
    return plan if plan in PAID_PLANS else "monthly"


def resolve_user_plan(db, user_id: str) -> str:
    """Effective plan for a user, kept in sync on `users.plan`.

    Fails open to 'free' (tracking still works; only the process cap applies).
    """
    user = (
        db.table("users")
        .select("email, plan")
        .eq("id", user_id)
        .execute()
    )
    if not user.data:
        return "free"
    email = (user.data[0].get("email") or "").lower().strip()
    stored = user.data[0].get("plan") or "free"

    customer = (
        db.table("customers")
        .select("plan, status")
        .eq("email", email)
        .execute()
    )
    effective = plan_from_customer_row(customer.data[0] if customer.data else None)

    if effective != stored:
        try:
            db.table("users").update({"plan": effective}).eq("id", user_id).execute()
        except Exception:
            pass
    return effective


def count_processes(db, user_id: str) -> int:
    rows = (
        db.table("processes")
        .select("id")
        .eq("user_id", user_id)
        .execute()
        .data
        or []
    )
    return len(rows)
