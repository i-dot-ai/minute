import re
from collections.abc import Iterator
from html.parser import HTMLParser

from common.database.postgres_models import DialogueEntry, JobStatus, Transcription
from common.types import SearchHighlight, TranscriptionSearchMatch, TranscriptionSearchSource

_BLOCK_TAGS = {
    "p",
    "br",
    "div",
    "li",
    "ul",
    "ol",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "blockquote",
    "pre",
    "hr",
    "table",
    "tr",
    "td",
    "th",
    "section",
}
_IGNORED_TAGS = {"script", "style", "head", "template"}
_PREVIEW_LIMITS = {"title": 1, "transcript": 3, "summary": 3, "speaker": 3}
_SNIPPET_LENGTH = 100
_CONTEXT_BEFORE = 30


class _SummaryTextParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.ignored_tag: str | None = None

    def handle_starttag(self, tag, attrs):  # noqa: ARG002
        if self.ignored_tag is None:
            if tag in _IGNORED_TAGS:
                self.ignored_tag = tag
                self.parts.append(" ")
            elif tag in _BLOCK_TAGS:
                self.parts.append(" ")

    def handle_endtag(self, tag):
        if tag == self.ignored_tag:
            self.ignored_tag = None
            self.parts.append(" ")
        elif self.ignored_tag is None and tag in _BLOCK_TAGS:
            self.parts.append(" ")

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_data(self, data):
        if self.ignored_tag is None:
            self.parts.append(data)


def summary_plain_text(html: str) -> str:
    parser = _SummaryTextParser()
    parser.feed(html)
    parser.close()
    return " ".join("".join(parser.parts).split())


def search_patterns(search: str) -> list[re.Pattern[str]]:
    words = {word.lower(): word for word in search.split()}
    return [re.compile(re.escape(word), re.IGNORECASE) for word in words.values()]


def _contains_all(texts: list[str], patterns: list[re.Pattern[str]]) -> bool:
    return all(any(pattern.search(text) for text in texts) for pattern in patterns)


def _utf16_length(text: str) -> int:
    return len(text.encode("utf-16-le")) // 2


def _excerpts(text: str, patterns: list[re.Pattern[str]]) -> Iterator[tuple[str, int, list[SearchHighlight]]]:
    spans = sorted(match.span() for pattern in patterns for match in pattern.finditer(text))
    previous_end = 0
    for index, (start, end) in enumerate(spans):
        if start < previous_end:
            continue
        window_start = max(previous_end, min(max(0, start - _CONTEXT_BEFORE), max(0, len(text) - _SNIPPET_LENGTH)))
        window_end = min(len(text), max(window_start + _SNIPPET_LENGTH, end))
        boundary = window_end
        # Include a keyword crossing the boundary, but do not keep extending into later hits.
        for next_start, next_end in spans[index:]:
            if next_start >= boundary:
                break
            window_end = max(window_end, next_end)
        merged: list[tuple[int, int]] = []
        for hit_start, hit_end in spans[index:]:
            if hit_start >= window_end:
                break
            if hit_end > window_end:
                continue
            if merged and hit_start < merged[-1][1]:
                merged[-1] = (merged[-1][0], max(hit_end, merged[-1][1]))
            else:
                merged.append((hit_start, hit_end))
        highlights = [
            SearchHighlight(
                start=_utf16_length(text[window_start:hit_start]),
                end=_utf16_length(text[window_start:hit_end]),
            )
            for hit_start, hit_end in merged
        ]
        yield text[window_start:window_end], _utf16_length(text[:window_start]), highlights
        previous_end = window_end


def _speaker_sources(entries: list[DialogueEntry], patterns: list[re.Pattern[str]]) -> Iterator[tuple[str, str, dict]]:
    speakers = set()
    for index, entry in enumerate(entries):
        name = entry["speaker"]
        if name.lower() not in speakers and _contains_all([name], patterns):
            speakers.add(name.lower())
            yield (
                "speaker",
                name,
                {
                    "entry_index": index,
                    "speaker": name,
                    "start_time": entry["start_time"],
                    "end_time": entry["end_time"],
                    "speech_excerpt": entry["text"][:_SNIPPET_LENGTH],
                },
            )


def matching_sources(
    transcription: Transcription, patterns: list[re.Pattern[str]], selected: set[TranscriptionSearchSource]
) -> Iterator[tuple[str, str, dict]]:
    title = transcription.title or ""
    if "title" in selected and _contains_all([title], patterns):
        yield "title", title, {}

    entries = (transcription.dialogue_entries or []) if transcription.status == JobStatus.COMPLETED else []
    if "speaker" in selected:
        yield from _speaker_sources(entries, patterns)

    if "summary" in selected:
        versions = sorted(
            (version for minute in transcription.minutes for version in minute.minute_versions),
            key=lambda version: (version.created_datetime, version.id),
            reverse=True,
        )
        for version in versions:
            if version.status != JobStatus.COMPLETED:
                continue
            text = summary_plain_text(version.html_content)
            if _contains_all([text], patterns):
                yield "summary", text, {"minute_id": version.minute_id, "minute_version_id": version.id}

    if "transcript" in selected and _contains_all([entry["text"] for entry in entries], patterns):
        for index, entry in enumerate(entries):
            if any(pattern.search(entry["text"]) for pattern in patterns):
                yield (
                    "transcript",
                    entry["text"],
                    {
                        "entry_index": index,
                        "speaker": entry["speaker"],
                        "start_time": entry["start_time"],
                        "end_time": entry["end_time"],
                    },
                )


def search_previews(
    sources: Iterator[tuple[str, str, dict]], patterns: list[re.Pattern[str]]
) -> tuple[list[TranscriptionSearchMatch], bool]:
    matches = []
    counts = dict.fromkeys(_PREVIEW_LIMITS, 0)
    truncated = False
    for source, text, location in sources:
        if counts[source] == _PREVIEW_LIMITS[source]:
            truncated = True
            continue
        for snippet, snippet_start, highlights in _excerpts(text, patterns):
            if counts[source] == _PREVIEW_LIMITS[source]:
                truncated = True
                break
            matches.append(
                TranscriptionSearchMatch(
                    source=source,
                    snippet=snippet,
                    snippet_start=snippet_start,
                    highlights=highlights,
                    **location,
                )
            )
            counts[source] += 1
    return matches, truncated
