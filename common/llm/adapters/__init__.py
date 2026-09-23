from .base import ModelAdapter

# The concrete adapter (GeminiModelAdapter) is intentionally NOT imported here.
# Importing it eagerly would pull in the provider SDK (google-genai) at import
# time, which prevents building provider-specific worker images. Import it lazily
# where needed (see common.llm.client.create_chatbot).
__all__ = ["ModelAdapter"]
