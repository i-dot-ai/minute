from __future__ import annotations

import dspy


class DialogSumSignature(dspy.Signature):
    """DialogSum-style conversational summarization.

    Dataset fields (knkarthick/dialogsum):
    - dialogue: text of dialogue
    - summary: human written summary of the dialogue
    """

    dialogue: str = dspy.InputField(desc="Text of dialogue.")
    summary: str = dspy.OutputField(desc="Human written summary of the dialogue.")


class JudgeRatingSignature(dspy.Signature):
    """Rate the candidate summary for the given criterion.

    Return an integer rating from 1 to 5.

    5: Excellent
    4: Good
    3: Mixed
    2: Poor
    1: Bad

    Provide a short reason.
    """

    dialogue: str = dspy.InputField(desc="Dialogue")
    reference_summary: str = dspy.InputField(desc="Gold summary from dataset")
    candidate_summary: str = dspy.InputField(desc="Model-generated summary")
    criterion: str = dspy.InputField(desc="One of: faithfulness, coverage, conciseness, coherence")

    rating: int = dspy.OutputField(desc="Integer 1-5")
    reason: str = dspy.OutputField(desc="Short explanation")
