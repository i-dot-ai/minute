"""
Script to generate an example.env file from settings.py
Groups variables by their 'category' value in json_schema_extra
"""

from collections import defaultdict
from pathlib import Path

from pydantic import Field
from pydantic_core import PydanticUndefinedType
from settings import Settings


def get_field_info(field: Field):
    """Extract field information including category and description"""
    category = field.json_schema_extra.get("category", "Other") if field.json_schema_extra else "Other"
    description = field.description or "No description provided"

    if field.default_factory:
        default = "'" + str(field.default_factory()).replace("'", '"') + "'"
    elif isinstance(field.default, PydanticUndefinedType) or field.default is None:
        default = "<please specify a value>"
    else:
        default = field.default

    return {
        "category": category,
        "description": description,
        "default": default,
    }


def generate_example_env():
    """Generate example.env file grouped by categories"""
    # Get all fields from the Settings class
    fields_by_category = defaultdict(list)

    # Iterate through all fields in the Settings class
    for field_name, field_info in Settings.model_fields.items():
        field_data = get_field_info(field_info)
        field_data["name"] = field_name
        field_data["type"] = field_info.annotation
        fields_by_category[field_data["category"]].append(field_data)

    # Generate the .env file content
    env_content = []
    env_content.append("# Example environment configuration file")
    env_content.append("# Copy this to .env and fill in the appropriate values")
    env_content.append("")

    # Sort categories alphabetically for consistent output
    for category in sorted(fields_by_category.keys()):
        fields = fields_by_category[category]

        # Add category header
        env_content.append(f"# {'=' * 50}")
        env_content.append(f"# {category.upper()}")
        env_content.append(f"# {'=' * 50}")
        env_content.append("")

        # Sort fields within category alphabetically
        for field in sorted(fields, key=lambda x: x["name"]):
            # Add description as comment
            env_content.append(f"# {field['description']}")
            # Format the environment variable
            default_val = field["default"]
            env_content.append(f"# {field['name']}={default_val}")
            env_content.append("")

    return "\n".join(env_content)


if __name__ == "__main__":
    """Main function to generate and write the example.env file"""
    env_content = generate_example_env()

    # Write to example.env file
    output_file = Path(__file__).parent.parent / ".env.example"
    with output_file.open("w") as f:
        f.write(env_content)

    print(f"Generated {output_file} with {len(env_content.splitlines())} lines")  # noqa: T201
    print(f"Found {len(Settings.model_fields)} environment variables")  # noqa: T201

    # Show categories found
    categories = set()
    for field_info in Settings.model_fields.values():
        category = field_info.json_schema_extra.get("category", "Other") if field_info.json_schema_extra else "Other"
        categories.add(category)

    print(f"Categories found: {', '.join(sorted(categories))}")  # noqa: T201
