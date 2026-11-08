import os
from typing import Optional
from backend.app.core.config import settings

def get_chat_model(
    provider: Optional[str] = None,
    model_name: Optional[str] = None,
    temperature: float = 0.7,
):
    """
    Factory function returning a LangChain-compatible ChatModel 
    for Gemini, OpenAI, Anthropic, or Ollama.
    """
    prov = (provider or settings.DEFAULT_PROVIDER).lower()

    if prov == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI
        api_key = settings.GEMINI_API_KEY or os.getenv("GEMINI_API_KEY")
        target_model = model_name or "gemini-2.5-flash"
        return ChatGoogleGenerativeAI(
            model=target_model,
            google_api_key=api_key,
            temperature=temperature,
        )

    elif prov == "openai":
        from langchain_openai import ChatOpenAI
        api_key = settings.OPENAI_API_KEY or os.getenv("OPENAI_API_KEY")
        target_model = model_name or "gpt-4o-mini"
        return ChatOpenAI(
            model=target_model,
            api_key=api_key,
            temperature=temperature,
        )

    elif prov == "anthropic":
        from langchain_anthropic import ChatAnthropic
        api_key = settings.ANTHROPIC_API_KEY or os.getenv("ANTHROPIC_API_KEY")
        target_model = model_name or "claude-3-5-sonnet-latest"
        return ChatAnthropic(
            model=target_model,
            api_key=api_key,
            temperature=temperature,
        )

    elif prov == "ollama":
        from langchain_community.chat_models import ChatOllama
        target_model = model_name or settings.OLLAMA_DEFAULT_MODEL
        return ChatOllama(
            base_url=settings.OLLAMA_BASE_URL,
            model=target_model,
            temperature=temperature,
        )

    else:
        raise ValueError(f"Unsupported model provider: '{prov}'. Supported: 'gemini', 'openai', 'anthropic', 'ollama'")

