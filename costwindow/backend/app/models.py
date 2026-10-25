from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    user_id: str
    email: str


class RefreshRequest(BaseModel):
    refresh_token: str


class ApiKeyResponse(BaseModel):
    api_key: str
    key_prefix: str
    message: str


class ApiKeyInfoResponse(BaseModel):
    has_key: bool
    key_prefix: Optional[str] = None
    created_at: Optional[str] = None
    last_used_at: Optional[str] = None


class IngestRequest(BaseModel):
    label: str
    provider: str
    model: str
    input_tokens: int
    output_tokens: int
    cached_tokens: int = 0
    cache_write_tokens: int = 0
    called_at: Optional[datetime] = None
    metadata: Optional[dict] = None
    billing_type: Optional[str] = None  # 'api' or 'subscription'


class IngestResponse(BaseModel):
    status: str
    cost_usd: Optional[float] = None
    process_id: Optional[str] = None
    reason: Optional[str] = None
    budget_state: Optional[str] = None     # 'ok' | 'warning' | 'exceeded'
    budget_used_pct: Optional[float] = None


class ProcessToggleRequest(BaseModel):
    is_active: Optional[bool] = None
    confirm: bool = False
    budget_usd_month: Optional[float] = None   # 0 or negative clears the budget
    budget_action: Optional[str] = None        # 'warn' | 'block'
    cost_driver: Optional[str] = None          # 'scheduled' | 'demand'


class AddProcessRequest(BaseModel):
    label: str
    provider: str
    description: Optional[str] = None
    billing_type: Optional[str] = 'api'
    subscription_id: Optional[str] = None


class ProcessLinkRequest(BaseModel):
    subscription_id: Optional[str] = None
    billing_type: Optional[str] = None


class ManualEntryRequest(BaseModel):
    label: str
    provider: str
    cost_usd: float
    called_at: datetime
    notes: Optional[str] = None


class ManualEntryUpdate(BaseModel):
    cost_usd: Optional[float] = None
    called_at: Optional[datetime] = None
    notes: Optional[str] = None


class UserSettingsUpdate(BaseModel):
    currency: Optional[str] = None
    spike_threshold: Optional[float] = None
    notifications_enabled: Optional[bool] = None


class SubscriptionCreate(BaseModel):
    name: str
    cost_gbp: float
    renewal_day: Optional[int] = None
    cancel_url: Optional[str] = None


class SubscriptionUpdate(BaseModel):
    name: Optional[str] = None
    cost_gbp: Optional[float] = None
    renewal_day: Optional[int] = None
    cancel_url: Optional[str] = None
    is_active: Optional[bool] = None


class BalanceEntryRequest(BaseModel):
    provider: str
    balance_usd: float


class EstimateRequest(BaseModel):
    provider: str
    model: str
    est_input_tokens: int
    est_output_tokens: int
    cached_tokens: int = 0
    runs_per_week: float = 1.0


class SubscriptionResponse(BaseModel):
    id: str
    name: str
    cost_gbp: float
    renewal_day: Optional[int]
    cancel_url: Optional[str]
    is_active: bool
    created_at: str
