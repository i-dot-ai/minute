from .base import ModelAdapter

# Concrete adapters (OpenAIModelAdapter, GeminiModelAdapter) are intentionally NOT
# imported here. Importing them eagerly would pull in every provider SDK
# (openai, google-genai) at import time, which prevents building provider-specific
# worker images. Import them lazily where needed (see common.llm.client.create_chatbot).
__all__ = ["ModelAdapter"]
