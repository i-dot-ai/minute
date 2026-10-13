import nh3

# Allowlist mirrors the template editor's output (see frontend/lib/sanitise.ts):
# formatting marks, headings and lists only, with no attributes.
_ALLOWED_TAGS = {"p", "br", "strong", "em", "s", "code", "h1", "h2", "h3", "h4", "ul", "ol", "li"}


def sanitize_template_html(content: str) -> str:
    """Strip any markup not emitted by the template editor before persistence."""
    return nh3.clean(content, tags=_ALLOWED_TAGS, attributes={})
