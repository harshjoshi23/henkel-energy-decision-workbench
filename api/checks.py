"""Vercel Python entry point for executed engine and adapter checks."""
from engine.adapter import ApiHandler


class handler(ApiHandler):
    endpoint = "/api/checks"
