from __future__ import annotations

from evals.summarisation.src.prompts import render_template


def test_render_template_contract_loads_file_and_renders_with_kwargs(tmp_path):
    """CONTRACT TEST: render_template must load template from file path and pass kwargs to Jinja2."""
    template_path = tmp_path / "template.jinja2"
    template_content = "Model: {{ model }}, Temperature: {{ temp }}"
    template_path.write_text(template_content, encoding="utf-8")

    model_name = "gpt-4"
    temperature = 0.7

    result = render_template(template_path, model=model_name, temp=temperature)

    assert model_name in result
    assert str(temperature) in result
