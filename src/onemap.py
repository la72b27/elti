"""OneMap Singapore API client for Cloudflare Workers.

Server-side only — all calls go directly from the Worker to OneMap,
avoiding browser CORS restrictions entirely.
"""

from js import fetch, Headers, Object
import json

TOKEN_URL = "https://www.onemap.gov.sg/api/auth/post/getToken"
SEARCH_URL = "https://www.onemap.gov.sg/api/common/elastic/search"
_KV_TOKEN_KEY = "onemap_token"
_TOKEN_TTL = 172800  # 2 days (token lasts 3 days)


async def get_token(env, force=False):
    """Return a valid OneMap Bearer token, using KV cache."""
    if not force:
        cached = await env.ELTI_DATA.get(_KV_TOKEN_KEY)
        if cached:
            return cached

    email = env.ONEMAP_EMAIL if hasattr(env, "ONEMAP_EMAIL") else None
    password = env.ONEMAP_PASSWORD if hasattr(env, "ONEMAP_PASSWORD") else None
    if not email or not password:
        print("[onemap] ONEMAP_EMAIL / ONEMAP_PASSWORD secrets not configured")
        return ""

    init = Object.new()
    init.method = "POST"
    init.body = json.dumps({"email": email, "password": password})
    init.headers = Headers.new([["Content-Type", "application/json"]])

    resp = await fetch(TOKEN_URL, init)
    text = await resp.text()
    data = json.loads(text)
    token = data.get("access_token", "")

    if token:
        try:
            await env.ELTI_DATA.put(_KV_TOKEN_KEY, token, expirationTtl=_TOKEN_TTL)
        except Exception:
            await env.ELTI_DATA.put(_KV_TOKEN_KEY, token)

    return token


async def search(env, query_string):
    """Proxy a OneMap elastic search request.

    query_string is forwarded verbatim (already URL-encoded by the client).
    Retries once with a fresh token on 401.
    """
    token = await get_token(env)

    for attempt in range(2):
        url = f"{SEARCH_URL}?{query_string}"
        init = Object.new()
        init.method = "GET"
        init.headers = Headers.new([["Authorization", token]])

        resp = await fetch(url, init)

        if resp.status == 401 and attempt == 0:
            token = await get_token(env, force=True)
            continue

        text = await resp.text()
        return json.loads(text)

    return {"results": []}
