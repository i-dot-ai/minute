from pathlib import Path

from jinja2 import Environment, FileSystemLoader, Template, select_autoescape

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"

ACTOR_GENERATOR_TEMPLATE = "actor_generator.j2"
ACTOR_SYSTEM_TEMPLATE = "actor_system.j2"
FACILITATOR_TEMPLATE = "facilitator.j2"
FACILITATOR_REMINDER_TEMPLATE = "facilitator_reminder.j2"
ENDING_NOTICE_TEMPLATE = "ending_notice.j2"

_jinja_environment = Environment(loader=FileSystemLoader(PROMPTS_DIR), autoescape=select_autoescape())


def get_template(template_name: str) -> Template:
    return _jinja_environment.get_template(template_name)
