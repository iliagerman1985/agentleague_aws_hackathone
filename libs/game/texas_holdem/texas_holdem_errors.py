from __future__ import annotations

from common.core.app_error import ErrorConfig


class TexasHoldemErrors:
    SCOPE = "texas_holdem"

    # General/gameflow
    GAME_OVER = ErrorConfig(scope=SCOPE, code="game_over", default_message="Game has already ended", http_status=400, retryable=False)
    PLAYER_NOT_ACTIVE = ErrorConfig(scope=SCOPE, code="player_not_active", default_message="Player is not active", http_status=400, retryable=False)
    NOT_PLAYER_TURN = ErrorConfig(scope=SCOPE, code="not_player_turn", default_message="Not player's turn", http_status=400, retryable=False)

    # Actions
    CANNOT_CHECK = ErrorConfig(scope=SCOPE, code="cannot_check", default_message="Cannot check when there is a bet to call", http_status=400, retryable=False)
    NO_BET_TO_CALL = ErrorConfig(scope=SCOPE, code="no_bet_to_call", default_message="No bet to call", http_status=400, retryable=False)
    NO_CHIPS = ErrorConfig(scope=SCOPE, code="no_chips", default_message="Player has no chips", http_status=400, retryable=False)
    MISSING_AMOUNT = ErrorConfig(scope=SCOPE, code="missing_amount", default_message="Raise requires an amount", http_status=400, retryable=False)
    RAISE_TOO_SMALL = ErrorConfig(scope=SCOPE, code="raise_too_small", default_message="Raise amount too small", http_status=400, retryable=False)
    RAISE_TOO_LARGE = ErrorConfig(scope=SCOPE, code="raise_too_large", default_message="Raise amount too large", http_status=400, retryable=False)
    INVALID_ACTION = ErrorConfig(scope=SCOPE, code="invalid_action", default_message="Invalid action", http_status=400, retryable=False)

    # Validation
    TOO_FEW_PLAYERS = ErrorConfig(scope=SCOPE, code="too_few_players", default_message="Must have at least 2 players", http_status=400, retryable=False)
    TOO_MANY_PLAYERS = ErrorConfig(scope=SCOPE, code="too_many_players", default_message="Cannot have more than 5 players", http_status=400, retryable=False)
    DUPLICATE_PLAYER_IDS = ErrorConfig(scope=SCOPE, code="duplicate_player_ids", default_message="Player IDs must be unique", http_status=400, retryable=False)
    DUPLICATE_POSITIONS = ErrorConfig(
        scope=SCOPE, code="duplicate_positions", default_message="Player positions must be unique", http_status=400, retryable=False
    )
    TOO_MANY_COMMUNITY_CARDS = ErrorConfig(
        scope=SCOPE, code="too_many_community_cards", default_message="Cannot have more than 5 community cards", http_status=400, retryable=False
    )
    INVALID_SUIT = ErrorConfig(scope=SCOPE, code="invalid_suit", default_message="Invalid suit", http_status=400, retryable=False)
    INVALID_RANK = ErrorConfig(scope=SCOPE, code="invalid_rank", default_message="Invalid rank", http_status=400, retryable=False)

    # Validation errors
    VALIDATION_ERROR = ErrorConfig(
        scope=SCOPE,
        code="validation_error",
        default_message="Validation failed",
        http_status=400,
        retryable=False,
    )
    INVALID_GAME_STATE = ErrorConfig(
        scope=SCOPE,
        code="invalid_game_state",
        default_message="Invalid game state",
        http_status=400,
        retryable=False,
    )
