from __future__ import annotations

import json
import os
import unittest
from urllib.request import Request, urlopen


def auth_headers(base_url: str) -> dict[str, str]:
    token = os.getenv("RAG_EVAL_TOKEN", "")
    if not token:
        email = os.getenv("RAG_EVAL_EMAIL", "")
        password = os.getenv("RAG_EVAL_PASSWORD", "")
        if email and password:
            request = Request(
                f"{base_url.rstrip('/')}/auth/login",
                data=json.dumps({"email": email, "password": password}).encode(),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urlopen(request, timeout=30) as response:
                token = json.load(response)["access_token"]
    if not token:
        raise unittest.SkipTest(
            "Set RAG_EVAL_TOKEN or RAG_EVAL_EMAIL/RAG_EVAL_PASSWORD for authenticated e2e tests"
        )
    return {"Authorization": f"Bearer {token}"}
