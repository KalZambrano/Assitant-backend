from app.ai.gemini_provider import GeminiProvider
from app.ai.ollama_provider import OllamaProvider
from app.ai.provider import AIProvider
from app.core.config import Settings


def create_provider(settings: Settings) -> AIProvider:
    if settings.ai_provider == "gemini":
        return GeminiProvider(settings.gemini_api_key or "", settings.gemini_model)
    if settings.ai_provider == "ollama":
        return OllamaProvider(settings.ollama_base_url, settings.ollama_model)
    raise ValueError(f"Proveedor no soportado: {settings.ai_provider}")
