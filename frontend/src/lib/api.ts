import axios from "axios";

const api = axios.create();

// BYOK: attach LLM config headers from localStorage
api.interceptors.request.use((config) => {
    const raw = localStorage.getItem("easypaper_llm_config");
    if (raw) {
        try {
            const llm = JSON.parse(raw);
            if (llm.apiKey) config.headers["X-LLM-API-Key"] = llm.apiKey;
            if (llm.baseUrl) config.headers["X-LLM-Base-URL"] = llm.baseUrl;
            if (llm.model) config.headers["X-LLM-Model"] = llm.model;
        } catch { /* ignore parse errors */ }
    }
    return config;
});

api.interceptors.response.use(
    (response) => response,
    (error) => {
        // No 401 redirect — BYOK mode has no auth
        return Promise.reject(error);
    },
);

export interface LLMConfig {
    baseUrl: string;
    apiKey: string;
    model: string;
}

export function getLLMConfig(): LLMConfig | null {
    const raw = localStorage.getItem("easypaper_llm_config");
    if (!raw) return null;
    try {
        const c = JSON.parse(raw);
        return c.apiKey ? c : null;
    } catch { return null; }
}

export function saveLLMConfig(config: LLMConfig) {
    localStorage.setItem("easypaper_llm_config", JSON.stringify(config));
}

export default api;
