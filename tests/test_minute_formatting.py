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


def test_strip_preamble():
    prose_draft = "The board met on 10 September 2026.\n\n## Actions\n"
    preceded_by_prose = "Here are the minutes.\n\n" + prose_draft
    no_heading = "The board met on 10 September 2026 [1]."
    preamble = (
        "An analysis of the transcript has been performed to map key details to the meeting summary. "
        "Below are the updated meeting minutes with citations added.\n\n"
    )
    cases = [
        # Commentary before the first heading is dropped.
        (DRAFT, preamble + DRAFT, DRAFT),
        # A clean minute is untouched.
        (DRAFT, DRAFT, DRAFT),
        # Templates that open with prose have no heading to anchor on, so nothing is dropped.
        (prose_draft, preceded_by_prose, preceded_by_prose),
        # Nothing to strip when the model returns no heading.
        (DRAFT, no_heading, no_heading),
    ]
    for draft, minute, expected in cases:
        assert strip_preamble(draft, minute) == expected


def test_unwrap_backticked_citations():
    minute = "The dry run finished on Friday `[1]`. Two findings were raised `[3-4][7]`."
    assert (
        unwrap_backticked_citations(minute) == "The dry run finished on Friday [1]. Two findings were raised [3-4][7]."
    )

    # Real code spans are left alone.
    code = "Daniel wrote the `normalise_address` step [3]."
    assert unwrap_backticked_citations(code) == code

    # The reason the unwrapping exists: mistune turns `[1]` into a <code> element.
    assert "<code>[1]</code>" in mistune.html("The dry run finished `[1]`.")
    assert "<code>" not in mistune.html(unwrap_backticked_citations("The dry run finished `[1]`."))


def test_combine_consecutive_citations_still_groups_runs():
    minute = "A statement [1][2][3] and another [9]."
    assert combine_consecutive_citations(minute) == "A statement [1-3] and another [9]."


def test_strip_document_code_fence():
    fenced = "```markdown\n# Meeting Minutes\n\n- A point\n```"
    assert strip_document_code_fence(fenced) == "# Meeting Minutes\n\n- A point"
    assert strip_document_code_fence(DRAFT) == DRAFT

    # The reason for stripping: a fenced minute renders as one code block instead of headings.
    assert "<pre>" in mistune.html(fenced)
    assert "<h1>" in mistune.html(strip_document_code_fence(fenced))
