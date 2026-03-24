from pathlib import Path

from common.llm.client import ChatBot
from evals.characteristics.src.config_loader import render_prompt
from evals.characteristics.src.sanitizer import sanitize_for_waf
from evals.characteristics.src.schema import (
    CharacteristicDetection,
    CharacteristicExtractionOutput,
)


def deduplicate_characteristics(characteristics: list[CharacteristicDetection]) -> list[CharacteristicDetection]:
    """Removes duplicate characteristics based on category and value."""
    unique_characteristics = []
    seen_signatures = set()

    for item in characteristics:
        category = item.characteristic
        value = item.attribute_value
        signature = f"{category}|{value}"

        if signature not in seen_signatures:
            seen_signatures.add(signature)
            unique_characteristics.append(item)

    return unique_characteristics


def build_chunks(transcript: str, chunk_size_chars: int = 1000, overlap_chars: int = 250) -> list[tuple[str, int]]:
    stride = chunk_size_chars - overlap_chars
    chunks = []
    start = 0
    while start < len(transcript):
        chunks.append((transcript[start : start + chunk_size_chars], start))
        start += stride
    return chunks


async def process_chunk(
    chunk_text: str, offset: int, prompt_path: Path, chatbot: ChatBot
) -> list[CharacteristicDetection]:
    safe_chunk = sanitize_for_waf(chunk_text)
    prompt_text = render_prompt(str(prompt_path), safe_chunk)
    response = await chatbot.structured_chat([{"role": "user", "content": prompt_text}], CharacteristicExtractionOutput)
    for item in response.detected_characteristics:
        for span in item.evidence_spans:
            if span.start_index is not None:
                span.start_index += offset
            if span.end_index is not None:
                span.end_index += offset
    return response.detected_characteristics
