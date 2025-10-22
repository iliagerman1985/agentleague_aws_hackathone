"""Parser for tool creation agent responses."""

import re
from typing import Any

from common.utils.utils import get_logger

logger = get_logger()


class ToolAgentResponseParser:
    """Parses agent responses to extract structured information."""

    @staticmethod
    def extract_code_blocks(content: str) -> list[dict[str, str]]:
        """Extract code blocks from markdown content.

        Args:
            content: Response content with markdown code blocks

        Returns:
            List of dictionaries with language and code
        """
        # Pattern to match ```language\ncode\n```
        pattern = r"```(\w+)?\n(.*?)```"
        matches = re.findall(pattern, content, re.DOTALL)

        code_blocks = []
        for language, code in matches:
            code_blocks.append(
                {
                    "language": language or "python",
                    "code": code.strip(),
                }
            )

        return code_blocks

    @staticmethod
    def extract_tool_metadata(content: str) -> dict[str, Any]:
        """Extract tool metadata from agent response.

        Args:
            content: Response content

        Returns:
            Dictionary with extracted metadata
        """
        metadata = {}

        # Try to extract tool name
        name_match = re.search(r"tool name[:\s]+['\"]?(\w+)['\"]?", content, re.IGNORECASE)
        if name_match:
            metadata["name"] = name_match.group(1)

        # Try to extract description
        desc_match = re.search(r"description[:\s]+['\"]?([^'\"]+)['\"]?", content, re.IGNORECASE)
        if desc_match:
            metadata["description"] = desc_match.group(1).strip()

        return metadata

    @staticmethod
    def parse_response(content: str) -> dict[str, Any]:
        """Parse agent response to extract all relevant information.

        Args:
            content: Agent response content

        Returns:
            Dictionary with parsed information
        """
        result = {
            "content": content,
            "code_blocks": ToolAgentResponseParser.extract_code_blocks(content),
            "metadata": ToolAgentResponseParser.extract_tool_metadata(content),
        }

        # Extract primary code block (first Python block)
        python_blocks = [block for block in result["code_blocks"] if block["language"] == "python"]

        if python_blocks:
            result["primary_code"] = python_blocks[0]["code"]

        return result

    @staticmethod
    def extract_test_scenario(content: str) -> dict[str, Any] | None:
        """Extract test scenario information from agent response.

        Args:
            content: Agent response content

        Returns:
            Dictionary with test scenario info or None
        """
        # Try to extract JSON state
        json_match = re.search(r"```json\n(.*?)```", content, re.DOTALL)
        if json_match:
            try:
                import json

                state = json.loads(json_match.group(1))
                return {
                    "game_state": state,
                    "description": "Test scenario from agent",
                }
            except json.JSONDecodeError:
                logger.warning("Failed to parse JSON from agent response")

        return None
