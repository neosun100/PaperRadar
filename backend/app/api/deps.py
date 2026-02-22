from fastapi import HTTPException, Request


def get_llm_config(request: Request) -> dict:
    """Extract LLM configuration from request headers (BYOK) or API token."""
    from ..core.config import get_config
    cfg = get_config()

    # 1. Check for API token — use server-side LLM config
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        token = auth[7:]
        if cfg.security.api_token and token == cfg.security.api_token:
            return {"base_url": cfg.llm.base_url, "api_key": cfg.llm.api_key, "model": cfg.llm.model}
        raise HTTPException(401, "Invalid API token")

    # 2. BYOK — LLM config from headers
    api_key = request.headers.get("X-LLM-API-Key", "")
    if api_key:
        return {
            "base_url": request.headers.get("X-LLM-Base-URL", ""),
            "api_key": api_key,
            "model": request.headers.get("X-LLM-Model", ""),
        }

    # 3. Fallback to config.yaml
    if cfg.llm.api_key and cfg.llm.api_key != "YOUR_API_KEY":
        return {"base_url": cfg.llm.base_url, "api_key": cfg.llm.api_key, "model": cfg.llm.model}

    raise HTTPException(400, "Missing X-LLM-API-Key header. Configure your API key in Settings.")


def get_client_id(request: Request) -> str:
    """Derive a client identity for per-user concurrency control."""
    # API token users share one identity
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return "_api_token_"
    # BYOK users: hash their API key (first 16 chars) as identity
    api_key = request.headers.get("X-LLM-API-Key", "")
    if api_key:
        return api_key[:16]
    return request.client.host if request.client else "_unknown_"
