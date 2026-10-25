from pydantic import BaseModel
from typing import Optional


class RegisterRequest(BaseModel):
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    user_id: str
    email: str


class RefreshRequest(BaseModel):
    refresh_token: str


class BriefPatch(BaseModel):
    content_md: Optional[str] = None
    status: Optional[str] = None  # draft | approved | archived
    is_public: Optional[bool] = None


class PostPatch(BaseModel):
    content: Optional[str] = None


class UserSettingsPatch(BaseModel):
    niche: Optional[str] = None
    subreddits: Optional[str] = None
    github_topics: Optional[str] = None
    web_queries: Optional[str] = None
    avoid_words: Optional[str] = None
    blotato_api_key: Optional[str] = None
    notify_email: Optional[str] = None


class NicheCreate(BaseModel):
    label: str = "My niche"
    niche: str = ""
    subreddits: str = ""
    github_topics: str = ""
    web_queries: str = ""
    rss_feeds: str = ""
    avoid_words: str = ""
    notify_email: Optional[str] = None
    active: bool = True


class NichePatch(BaseModel):
    label: Optional[str] = None
    niche: Optional[str] = None
    subreddits: Optional[str] = None
    github_topics: Optional[str] = None
    web_queries: Optional[str] = None
    rss_feeds: Optional[str] = None
    avoid_words: Optional[str] = None
    notify_email: Optional[str] = None
    active: Optional[bool] = None
