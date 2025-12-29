"""Tests for tool schema validation."""

import pytest

from deubot.tools import get_tools

pytestmark = pytest.mark.unit


def test_strict_tools_have_all_properties_required():
    """
    OpenAI strict mode requires all properties to be in the 'required' array.
    This test catches schema errors before they hit the API.
    """
    tools = get_tools()

    for tool in tools:
        if not tool.get("strict"):
            continue

        name = tool["name"]
        params = tool["parameters"]
        properties = set(params.get("properties", {}).keys())
        required = set(params.get("required", []))

        assert properties == required, (
            f"Tool '{name}' has strict=true but 'required' doesn't match 'properties'. "
            f"Missing from required: {properties - required}. "
            f"Extra in required: {required - properties}"
        )


def test_strict_nested_objects_have_all_properties_required():
    """Check nested objects in strict tools also have all properties required."""
    tools = get_tools()

    for tool in tools:
        if not tool.get("strict"):
            continue

        name = tool["name"]
        _check_nested_objects(name, tool["parameters"])


def _check_nested_objects(tool_name: str, schema: dict, path: str = ""):
    """Recursively check that all nested objects have matching properties and required."""
    if schema.get("type") == "object":
        properties = set(schema.get("properties", {}).keys())
        required = set(schema.get("required", []))

        if properties != required:
            location = f" at {path}" if path else ""
            raise AssertionError(
                f"Tool '{tool_name}'{location} has mismatched properties/required. "
                f"Missing: {properties - required}. Extra: {required - properties}"
            )

        for prop_name, prop_schema in schema.get("properties", {}).items():
            new_path = f"{path}.{prop_name}" if path else prop_name
            _check_nested_objects(tool_name, prop_schema, new_path)

    elif schema.get("type") == "array" and "items" in schema:
        new_path = f"{path}[]" if path else "[]"
        _check_nested_objects(tool_name, schema["items"], new_path)
