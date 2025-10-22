"""Pure code generation and validation tools for the tool creation agent.

These tools do NOT interact with the database. They only generate, validate,
and analyze code. The UI handles all persistence.
"""

import ast
import json
from typing import Any

from strands import tool

from common.agents.models import (
    ImprovementSuggestion,
    ImprovementSuggestions,
    ToolCreationContext,
    ValidationResult,
)


@tool
def validate_code_syntax(code: str) -> ValidationResult:
    """Validate Python code syntax.

    This is a pure validation function that checks if the code is syntactically
    correct Python. It does NOT execute the code or save it anywhere.

    Args:
        code: Python code to validate

    Returns:
        ValidationResult with validation status and any errors
    """
    errors: list[str] = []
    warnings: list[str] = []

    try:
        # Parse the code to check syntax
        tree = ast.parse(code)

        # Check for lambda_handler function
        has_lambda_handler = False
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "lambda_handler":
                has_lambda_handler = True

                # Check function signature
                if len(node.args.args) != 2:
                    errors.append("lambda_handler must take exactly 2 arguments: event and context")
                elif node.args.args[0].arg != "event" or node.args.args[1].arg != "context":
                    warnings.append("lambda_handler arguments should be named 'event' and 'context'")

                break

        if not has_lambda_handler:
            errors.append("Code must contain a lambda_handler(event, context) function")

        # Check for return statement
        has_return = False
        for node in ast.walk(tree):
            if isinstance(node, ast.Return):
                has_return = True
                break

        if not has_return:
            warnings.append("lambda_handler should have a return statement")

        if errors:
            return ValidationResult(
                is_valid=False,
                errors=errors,
                warnings=warnings,
                message="Code has validation errors",
            )

        return ValidationResult(
            is_valid=True,
            errors=[],
            warnings=warnings,
            message="Code is syntactically valid" + (f" ({len(warnings)} warnings)" if warnings else ""),
        )

    except SyntaxError as e:
        return ValidationResult(
            is_valid=False,
            errors=[f"Syntax error at line {e.lineno}: {e.msg}"],
            warnings=[],
            message="Code has syntax errors",
        )
    except Exception as e:
        return ValidationResult(
            is_valid=False,
            errors=[f"Validation error: {e!s}"],
            warnings=[],
            message="Code validation failed",
        )


@tool
def suggest_improvements(
    code: str,
    context: ToolCreationContext[Any, Any, Any],
) -> ImprovementSuggestions:
    """Suggest improvements to tool code.

    This is a pure analysis function that suggests improvements based on
    best practices and the environment context. It does NOT modify the code
    or save anything.

    Args:
        code: Python code to analyze
        context: Tool creation context with environment-specific information

    Returns:
        ImprovementSuggestions with suggestions and optionally improved code
    """
    suggestions: list[ImprovementSuggestion] = []

    try:
        tree = ast.parse(code)

        # Check for error handling
        has_try_except = False
        for node in ast.walk(tree):
            if isinstance(node, ast.Try):
                has_try_except = True
                break

        if not has_try_except:
            suggestions.append(
                ImprovementSuggestion(
                    category="error_handling",
                    description="Add try/except blocks to handle errors gracefully",
                    code_snippet="""try:
    # Your tool logic here
    result = calculate_something(state)
    return {"result": result, "explanation": "..."}
except Exception as e:
    return {"error": str(e), "explanation": "Tool execution failed"}""",
                )
            )

        # Check for docstring
        has_docstring = False
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "lambda_handler":
                if ast.get_docstring(node):
                    has_docstring = True
                break

        if not has_docstring:
            suggestions.append(
                ImprovementSuggestion(
                    category="documentation",
                    description="Add a docstring to explain what the tool does",
                    code_snippet='''def lambda_handler(event, context):
    """Calculate pot odds for calling decisions.
    
    Args:
        event: Contains state and player_id
        context: Execution context
        
    Returns:
        Dictionary with pot odds calculation
    """''',
                )
            )

        # Check for explanation in return
        code_lower = code.lower()
        if '"explanation"' not in code_lower and "'explanation'" not in code_lower:
            suggestions.append(
                ImprovementSuggestion(
                    category="usability",
                    description="Include an 'explanation' field in the return value to help agents understand the result",
                    code_snippet="""return {
    "result": calculated_value,
    "explanation": "This is what the tool calculated and why"
}""",
                )
            )

        # Environment-specific suggestions
        for constraint in context.constraints:
            if "cannot modify" in constraint.lower() and "state" in code_lower and "=" in code:
                # Check if code might be modifying state
                suggestions.append(
                    ImprovementSuggestion(
                        category="constraints",
                        description=f"Ensure you're not violating this constraint: {constraint}",
                        code_snippet=None,
                    )
                )

        return ImprovementSuggestions(
            suggestions=suggestions,
            improved_code=None,  # We don't auto-generate improved code, just suggest
        )

    except Exception as e:
        return ImprovementSuggestions(
            suggestions=[
                ImprovementSuggestion(
                    category="error",
                    description=f"Could not analyze code: {e!s}",
                    code_snippet=None,
                )
            ],
            improved_code=None,
        )


@tool
def explain_schema(
    schema_path: str,
    context: ToolCreationContext[Any, Any, Any],
) -> str:
    """Explain a specific part of the environment schema.

    This is a pure explanation function that helps users understand the
    schema structure. It does NOT modify anything.

    Args:
        schema_path: JSON path to the schema element (e.g., "properties.pot")
        context: Tool creation context with schema information

    Returns:
        Human-readable explanation of the schema element
    """
    try:
        # Parse the path
        parts = schema_path.split(".")

        # Navigate to the schema element
        current = context.state_schema
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return f"Schema path '{schema_path}' not found in state schema"

        # Format the explanation
        if isinstance(current, dict):
            explanation = f"Schema element at '{schema_path}':\n\n"
            explanation += json.dumps(current, indent=2)

            # Add human-readable description if available
            if "description" in current:
                explanation += f"\n\nDescription: {current['description']}"
            if "type" in current:
                explanation += f"\nType: {current['type']}"
            if "properties" in current:
                properties_dict: dict[str, Any] = current["properties"]
                explanation += f"\nProperties: {', '.join(properties_dict.keys())}"

            return explanation
        else:
            return f"Schema element at '{schema_path}': {current}"

    except Exception as e:
        return f"Error explaining schema: {e!s}"
