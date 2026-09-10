"""Guards against model output that Markdown rendering turns into a broken minute."""

import mistune

from common.services.minute_handler_service import strip_document_code_fence
from common.templates.citations import (
    combine_consecutive_citations,
    strip_preamble,
    unwrap_backticked_citations,
)

DRAFT = """# Meeting Minutes: Delivery Board

## 1. Meeting Overview

- **Date:** 10 September 2026
"""


def test_strip_preamble_removes_commentary_before_the_first_heading():
    minute = (
        "An analysis of the transcript has been performed to map key details to the meeting summary. "
        "Below are the updated meeting minutes with citations added.\n\n" + DRAFT
    )
    assert strip_preamble(DRAFT, minute) == DRAFT


def test_strip_preamble_leaves_a_clean_minute_untouched():
    assert strip_preamble(DRAFT, DRAFT) == DRAFT


def test_strip_preamble_keeps_content_when_the_draft_does_not_start_with_a_heading():
    """Templates that open with prose have no heading to anchor on, so nothing is dropped."""
    draft = "The board met on 10 September 2026.\n\n## Actions\n"
    minute = "Here are the minutes.\n\n" + draft
    assert strip_preamble(draft, minute) == minute


def test_strip_preamble_keeps_content_when_the_model_returns_no_heading():
    minute = "The board met on 10 September 2026 [1]."
    assert strip_preamble(DRAFT, minute) == minute


def test_unwrap_backticked_citations():
    minute = "The dry run finished on Friday `[1]`. Two findings were raised `[3-4][7]`."
    expected = "The dry run finished on Friday [1]. Two findings were raised [3-4][7]."
    assert unwrap_backticked_citations(minute) == expected


def test_unwrap_backticked_citations_leaves_real_code_spans_alone():
    minute = "Daniel wrote the `normalise_address` step [3]."
    assert unwrap_backticked_citations(minute) == minute


def test_backticked_citations_would_otherwise_render_as_code():
    """The reason the unwrapping exists: mistune turns `[1]` into a <code> element."""
    assert "<code>[1]</code>" in mistune.html("The dry run finished `[1]`.")
    assert "<code>" not in mistune.html(unwrap_backticked_citations("The dry run finished `[1]`."))


def test_combine_consecutive_citations_still_groups_runs():
    minute = "A statement [1][2][3] and another [9]."
    assert combine_consecutive_citations(minute) == "A statement [1-3] and another [9]."


def test_strip_document_code_fence_unwraps_a_fenced_minute():
    fenced = "```markdown\n# Meeting Minutes\n\n- A point\n```"
    assert strip_document_code_fence(fenced) == "# Meeting Minutes\n\n- A point"


def test_strip_document_code_fence_leaves_an_unfenced_minute_alone():
    assert strip_document_code_fence(DRAFT) == DRAFT


def test_fenced_minute_would_otherwise_render_as_one_code_block():
    fenced = "```markdown\n# Meeting Minutes\n\n- A point\n```"
    assert "<pre>" in mistune.html(fenced)
    assert "<h1>" in mistune.html(strip_document_code_fence(fenced))
