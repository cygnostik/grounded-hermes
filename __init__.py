"""Hermes Agent entry point for Grounded Hermes."""

from pathlib import Path

from .grounded.service import register_tools


def register(ctx):
    register_tools(ctx)
    ctx.register_skill(
        "ground-news", Path(__file__).resolve().parent / "skills" / "ground-news" / "SKILL.md"
    )
