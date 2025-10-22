"""Template variable substitution using Jinja2.

This module provides utilities for substituting template variables in strings
using Jinja2 templating engine. It converts the custom ${{variable}} syntax
to standard Jinja2 {{variable}} syntax and handles complex nested paths.

Example usage:
    template = "Player ${{state.players[0].name}} has ${{state.players[0].chips}} chips"
    data = {"state": {"players": [{"name": "John", "chips": 1000}]}}
    result = substitute_template_variables(template, data)
    # Result: "Player John has 1000 chips"
"""

import re
from typing import Any

from jinja2 import Environment, TemplateError, Undefined, UndefinedError
from pydantic import BaseModel

from common.utils.utils import get_logger

logger = get_logger(__name__)


class TemplateSubstitutionError(Exception):
    """Exception raised when template substitution fails."""

    def __init__(self, message: str, template: str, error: Exception | None = None):
        self.message = message
        self.template = template
        self.original_error = error
        super().__init__(message)


def substitute_template_variables(
    template: str,
    data: dict[str, Any] | BaseModel,
    strict: bool = False,
) -> str:
    """Substitute template variables using Jinja2.

    Converts ${{variable.path}} syntax to Jinja2 {{variable.path}} and renders
    the template with the provided data.

    Args:
        template: Template string with ${{variable}} syntax
        data: Data dictionary or Pydantic model to use for substitution
        strict: If True, raises exception on undefined variables. If False,
                leaves undefined variables as-is.

    Returns:
        String with variables substituted

    Raises:
        TemplateSubstitutionError: If template rendering fails and strict=True
    """
    if not template:
        return template

    try:
        # Convert Pydantic model to dict if needed
        if isinstance(data, BaseModel):
            template_data = data.model_dump()
        else:
            template_data = data or {}

        # Convert ${{variable}} to {{variable}} for Jinja2
        jinja_template_str = _convert_template_syntax(template)

        # Create Jinja2 environment with appropriate settings
        env = Environment(
            # Don't auto-escape HTML since we're not rendering HTML
            autoescape=False,
            # Handle undefined variables based on strict mode
            undefined=_StrictUndefined if strict else _SilentUndefined,
        )

        # Create and render template
        jinja_template = env.from_string(jinja_template_str)
        result = jinja_template.render(**template_data)

        logger.debug(f"Template substitution successful: {len(template)} chars -> {len(result)} chars")
        return result

    except (TemplateError, UndefinedError) as e:
        error_msg = f"Template rendering failed: {e!s}"
        logger.error(f"{error_msg} | Template: {template[:100]}...")

        if strict:
            raise TemplateSubstitutionError(error_msg, template, e)
        # In non-strict mode, return original template on error
        logger.warning(f"Returning original template due to error: {error_msg}")
        return template

    except Exception as e:
        error_msg = f"Unexpected error during template substitution: {e!s}"
        logger.exception(f"{error_msg} | Template: {template[:100]}...")

        if strict:
            raise TemplateSubstitutionError(error_msg, template, e)
        return template


def _convert_template_syntax(template: str) -> str:
    """Convert ${{variable}} syntax to {{variable}} for Jinja2.

    Args:
        template: Template string with ${{variable}} syntax

    Returns:
        Template string with {{variable}} syntax
    """
    # Replace ${{variable}} with {{variable}}
    # Use a more precise regex to avoid issues with nested braces
    pattern = r"\$\{\{([^}]+)\}\}"
    jinja_template = re.sub(pattern, r"{{\1}}", template)

    return jinja_template


class _SilentUndefined(Undefined):
    """Custom undefined class that returns the original variable syntax."""

    def __str__(self) -> str:
        return f"${{{{{self._undefined_name}}}}}"

    def __repr__(self) -> str:
        return f"${{{{{self._undefined_name}}}}}"


class _StrictUndefined(Undefined):
    """Custom undefined class that raises exceptions for undefined variables."""

    def __str__(self) -> str:
        raise UndefinedError(f"Variable '{self._undefined_name}' is undefined")

    def __repr__(self) -> str:
        raise UndefinedError(f"Variable '{self._undefined_name}' is undefined")


def validate_template_variables(
    template: str,
    available_variables: dict[str, Any] | BaseModel,
) -> tuple[bool, list[str], list[str]]:
    """Validate that all variables in template are available in the data.

    Args:
        template: Template string with ${{variable}} syntax
        available_variables: Available data for substitution

    Returns:
        Tuple of (is_valid, missing_variables, found_variables)
    """
    if not template:
        return True, [], []

    try:
        # Extract all variable references from template
        pattern = r"\$\{\{([^}]+)\}\}"
        variable_refs = re.findall(pattern, template)

        if not variable_refs:
            return True, [], []

        # Convert data to dict if needed
        if isinstance(available_variables, BaseModel):
            data = available_variables.model_dump()
        else:
            data = available_variables or {}

        missing_vars: list[str] = []
        found_vars: list[str] = []

        for var_ref in variable_refs:
            var_ref = var_ref.strip()
            try:
                # Try to substitute just this variable to see if it exists
                test_template = f"{{{{{var_ref}}}}}"
                env = Environment(undefined=_StrictUndefined)
                template_obj = env.from_string(test_template)
                _ = template_obj.render(**data)
                found_vars.append(var_ref)
            except (TemplateError, UndefinedError):
                missing_vars.append(var_ref)

        is_valid = len(missing_vars) == 0
        return is_valid, missing_vars, found_vars

    except Exception as e:
        logger.exception(f"Error validating template variables: {e}")
        return False, [f"Validation error: {e!s}"], []
