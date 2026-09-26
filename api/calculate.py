"""Vercel Python entry point; no filesystem mutations or external requests."""
from engine.adapter import ApiHandler


class handler(ApiHandler):
    endpoint = "/api/calculate"
