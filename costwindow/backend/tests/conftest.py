import pytest
from httpx import AsyncClient, ASGITransport
import sys
import os

# Add backend dir to path so `from app.X import Y` works
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from main import app


@pytest.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c
