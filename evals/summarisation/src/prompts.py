from __future__ import annotations

from pathlib import Path

from jinja2 import Template


def render_template(path: str | Path, **kwargs: object) -> str:
    text = Path(path).read_text(encoding="utf-8")
    template = Template(text)
    return template.render(**kwargs)
