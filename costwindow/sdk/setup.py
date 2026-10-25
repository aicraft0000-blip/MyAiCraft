from pathlib import Path
from setuptools import setup, find_packages

_here = Path(__file__).parent
_long = (_here / "README.md").read_text(encoding="utf-8") if (_here / "README.md").exists() else ""

setup(
    name="costwindow",
    version="0.2.0",
    description="The control layer for autonomous AI spend — track, budget, and hard-stop your AI API usage.",
    long_description=_long,
    long_description_content_type="text/markdown",
    url="https://costwindow.com",
    project_urls={
        "Homepage": "https://costwindow.com",
        "Source": "https://github.com/aicraft0000-blip/costwindow-sdk",
    },
    license="MIT",
    packages=find_packages(exclude=["tests", "tests.*"]),
    python_requires=">=3.9",
    install_requires=["requests>=2.28"],
    extras_require={
        "anthropic": ["anthropic>=0.39"],
        "openai":    ["openai>=1.0"],
        "all":       ["anthropic>=0.39", "openai>=1.0"],
    },
)
