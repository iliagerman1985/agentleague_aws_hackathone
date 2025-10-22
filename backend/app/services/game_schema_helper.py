from __future__ import annotations

import json
from typing import Any

from game_api import GenericGameEnv


def build_player_view_schema(env_class: type[GenericGameEnv]) -> str:
    """Return the authoritative player-view JSON schema for the given game env.

    The schema is produced from the game’s Pydantic player-view model using
    camelCase aliases (by_alias=True) which matches how our JsonModel is configured.

    Args:
        env_class: The game environment class (e.g., TexasHoldemEnv)

    Returns:
        A pretty-printed JSON string of the model schema suitable for prompt injection.
    """
    view_type = env_class.types().player_view_type()
    schema: dict[str, Any] = view_type.model_json_schema(by_alias=True)
    return json.dumps(schema, indent=2)
