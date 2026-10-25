from fastapi import APIRouter, Depends, HTTPException
from app.dependencies import get_user_from_jwt
from app.models import EstimateRequest
from app.pricing import calculate_cost, PRICING
from app.budgets import WEEKS_PER_MONTH

router = APIRouter()


@router.post("/estimate")
def estimate(req: EstimateRequest, _user_id: str = Depends(get_user_from_jwt)):
    """Pre-flight price tag: what would this task cost before it ever runs?"""
    if req.provider not in PRICING:
        raise HTTPException(status_code=400, detail=f"Unknown provider '{req.provider}'")

    cost_per_run = calculate_cost(
        req.provider, req.model,
        req.est_input_tokens, req.est_output_tokens, req.cached_tokens,
    )
    if cost_per_run == 0.0 and (req.est_input_tokens or req.est_output_tokens):
        raise HTTPException(
            status_code=400,
            detail=f"Unknown model '{req.model}' for provider '{req.provider}'",
        )

    monthly = cost_per_run * req.runs_per_week * WEEKS_PER_MONTH
    return {
        "provider":            req.provider,
        "model":               req.model,
        "cost_per_run_usd":    round(cost_per_run, 6),
        "runs_per_week":       req.runs_per_week,
        "projected_month_usd": round(monthly, 4),
    }


@router.get("/estimate/models")
def estimate_models(_user_id: str = Depends(get_user_from_jwt)):
    """Providers and models the estimator knows prices for."""
    return {p: sorted(models.keys()) for p, models in PRICING.items()}
