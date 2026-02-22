from fastapi import HTTPException, Request


def get_llm_config(request: Request) -> dict:
    """Extract LLM configuration from request headers (BYOK)."""
    base_url = request.headers.get("X-LLM-Base-URL", "")
    api_key = request.headers.get("X-LLM-API-Key", "")
    model = request.headers.get("X-LLM-Model", "")
    if not api_key:
        # Fallback to config.yaml
        from ..core.config import get_config
        cfg = get_config()
        if cfg.llm.api_key and cfg.llm.api_key != "YOUR_API_KEY":
            return {"base_url": cfg.llm.base_url, "api_key": cfg.llm.api_key, "model": cfg.llm.model}
        raise HTTPException(400, "Missing X-LLM-API-Key header. Configure your API key in Settings.")
    return {"base_url": base_url, "api_key": api_key, "model": model}
