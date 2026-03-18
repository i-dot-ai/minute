import dspy

from evals.summarisation.src.signatures import DialogSumSignature, JudgeRatingSignature


def test_dialog_sum_signature_contract_extends_dspy_signature():
    """CONTRACT TEST: DialogSumSignature must be a DSPy Signature for LLM prompting."""
    assert issubclass(DialogSumSignature, dspy.Signature)


def test_dialog_sum_signature_contract_has_required_fields():
    """CONTRACT TEST: DialogSumSignature must have dialogue input and summary output fields."""
    required_input_fields = ["dialogue"]
    required_output_fields = ["summary"]

    fields = DialogSumSignature.model_fields

    for field_name in required_input_fields:
        assert field_name in fields, f"Missing required input field: {field_name}"

    for field_name in required_output_fields:
        assert field_name in fields, f"Missing required output field: {field_name}"


def test_judge_rating_signature_contract_extends_dspy_signature():
    """CONTRACT TEST: JudgeRatingSignature must be a DSPy Signature for LLM prompting."""
    assert issubclass(JudgeRatingSignature, dspy.Signature)


def test_judge_rating_signature_contract_has_required_fields():
    """CONTRACT TEST: JudgeRatingSignature must have all input fields for judging and output fields for rating."""
    required_input_fields = ["dialogue", "reference_summary", "candidate_summary", "criterion"]
    required_output_fields = ["rating", "reason"]

    fields = JudgeRatingSignature.model_fields

    for field_name in required_input_fields:
        assert field_name in fields, f"Missing required input field: {field_name}"

    for field_name in required_output_fields:
        assert field_name in fields, f"Missing required output field: {field_name}"


def test_judge_rating_signature_contract_rating_field_type():
    """CONTRACT TEST: JudgeRatingSignature rating field must be integer type for 1-5 scale."""
    rating_field = JudgeRatingSignature.model_fields["rating"]
    assert rating_field.annotation is int, "Rating field must be integer type for 1-5 scale"
