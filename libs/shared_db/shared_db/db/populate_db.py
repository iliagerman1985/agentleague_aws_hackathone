"""Database population script for AgentLeague.

This script populates the database with:
1. System-wide predefined chess test scenarios (11 positions)
2. The existing chess piece analysis tool
3. Predefined agents (Chess and Texas Hold'em)
4. LLM integration (Google Gemini or AWS Bedrock fallback)

The script is idempotent and can be run multiple times safely.
It uses predefined IDs to ensure consistency across database resets.
"""

import sys
from typing import Any, TypedDict

import chess
from game_api import GameType
from sqlalchemy import delete, select

from app.utils.encryption import encrypt_api_key
from common.core.config_service import ConfigService
from common.enums import LLMProvider
from common.ids import UserId
from common.utils.tsid import TSID
from common.utils.utils import get_logger
from shared_db.db import AsyncSessionLocal
from shared_db.models.agent import Agent, AgentVersion, AgentVersionTool, TestScenario, Tool
from shared_db.models.llm_enums import AnthropicModel, AWSBedrockModel, GoogleModel, OpenAIModel
from shared_db.models.llm_integration import LLMIntegration
from shared_db.models.tool import ToolValidationStatus
from shared_db.models.user import AvatarType, User, UserRole


class ChessPosition(TypedDict):
    """Type definition for chess position data."""

    name: str
    fen: str
    description: str
    tags: list[str]


class UserData(TypedDict):
    """Type definition for predefined user data."""

    id: int
    email: str
    cognito_sub: str
    username: str
    full_name: str
    role: "UserRole"
    avatar_filename: str


class LLMConfig(TypedDict):
    """Configuration data for predefined LLM integrations."""

    provider: "LLMProvider"
    model: str
    display_name: str
    api_key: str
    priority: int


def tsid_to_int(value: int | str | TSID | UserId) -> int:
    """Normalize TSID-like identifiers to raw integers."""
    match value:
        case TSID():
            return value.number
        case int():
            return value
        case str():
            return TSID.from_string_by_length(value).number
        case _:
            return int(value)


# Configure logging
logger = get_logger()

# Predefined user IDs with their emails and cognito_sub for reference
# Using raw integers instead of wrapped TSID objects to avoid SQLAlchemy sentinel value issues
PREDEFINED_USERS: dict[str, UserData] = {
    "admin_user": {
        "id": 760447946411413760,
        "email": "admin@agentleague.app",
        "cognito_sub": "24d88468-d081-70cb-f9b5-32169351213a",
        "username": "admin",
        "full_name": "Administrator",
        "role": UserRole.ADMIN,
        "avatar_filename": "splinter.png",
    },
    "yevgeny_user": {
        "id": 760447946411413761,
        "email": "yevgeny.krasik@agentleague.app",
        "cognito_sub": "34b80428-00c1-707a-fffd-3dd612463840",
        "username": "yevgeny",
        "full_name": "Yevgeny Krasik",
        "role": UserRole.ADMIN,
        "avatar_filename": "yevgeny.jpg",
    },
    "ilia_german_user": {
        "id": 760447946411413763,
        "email": "ilia.german@agentleague.app",
        "cognito_sub": "c4f89498-00a1-7019-bc68-108b7c414542",
        "username": "ilia_german",
        "full_name": "Ilia German",
        "role": UserRole.ADMIN,
        "avatar_filename": "ilia.jpg",
    },
    "gil_pali_user": {
        "id": 760447946411413764,
        "email": "gil.pali@agentleague.app",
        "cognito_sub": "e4887448-40b1-7000-2c2f-afeb67905a5a",
        "username": "gil",
        "full_name": "Gil Pali",
        "role": UserRole.ADMIN,
        "avatar_filename": "gilp.jpg",
    },
    "rohan_karmarkar_user": {
        "id": 760447946411413765,
        "email": "rohan.karmarkar@agentleague.ai",
        "cognito_sub": "0498a408-3021-7016-69d2-29e9ea412845",
        "username": "rohan",
        "full_name": "Rohan Karmarkar",
        "role": UserRole.USER,
        "avatar_filename": "rohan.jpeg",
    },
    "raghvender_krni_user": {
        "id": 760447946411413766,
        "email": "raghvender.krni@agentleague.ai",
        "cognito_sub": "44189498-e0c1-7008-304a-6e3d23975a68",
        "username": "raghvender",
        "full_name": "Raghvender Krni",
        "role": UserRole.USER,
        "avatar_filename": "raghvender.jpeg",
    },
    "rory_richardson_user": {
        "id": 760447946411413767,
        "email": "rory.richardson@agentleague.ai",
        "cognito_sub": "a4b86438-b041-70b6-e6ac-779fff877952",
        "username": "rory",
        "full_name": "Rory Richardson",
        "role": UserRole.USER,
        "avatar_filename": "rory.jpeg",
    },
    "kamini_aisola_user": {
        "id": 760447946411413768,
        "email": "kamini.Aisola@agentleague.ai",
        "cognito_sub": "e41804f8-c091-7033-6b03-d8cc093258b6",
        "username": "kamini",
        "full_name": "Kamini Aisola",
        "role": UserRole.USER,
        "avatar_filename": "kamini.jpeg",
    },
}

# Extract just the IDs for backward compatibility
PREDEFINED_USER_IDS: dict[str, int] = {key: value["id"] for key, value in PREDEFINED_USERS.items()}

# Predefined IDs for consistency across database resets (using raw integers)
# Using raw integers instead of wrapped TSID objects to avoid SQLAlchemy sentinel value issues
PREDEFINED_IDS: dict[str, int] = {
    "tool_attack_detector": 767336733232787178,  # Attack Detector tool
    "tool_check_protected": 767665207287407021,  # Check Protected Tools
    "tool_move_validator": 768057106417224226,  # Move Validator tool
    "tool_poker_hand_evaluator": 760551427867515833,  # New poker tool ID
    "agent_chess": 760453725797653372,  # Existing chess agent ID
    "agent_chess_2": 800000000000001001,  # Second chess agent for matchmaking
    "agent_chess_stockfish": 800000000000001007,  # Stockfish Brain bot for playground only
    "agent_poker": 760453561563090814,  # Existing poker agent ID
    "agent_poker_2": 800000000000001002,  # Second poker agent for matchmaking (Shredder)
    "agent_poker_3": 800000000000001005,  # Third poker agent for matchmaking (Benedict)
    "agent_version_chess": 760551615699982538,  # Existing chess agent version ID
    "agent_version_chess_2": 800000000000001003,  # Second chess agent version
    "agent_version_chess_stockfish": 800000000000001008,  # Stockfish Brain agent version
    "agent_version_poker": 760453561924852584,  # Existing poker agent version ID
    "agent_version_poker_2": 800000000000001004,  # Second poker agent version
    "agent_version_poker_3": 800000000000001006,  # Third poker agent version
    "admin_user": PREDEFINED_USER_IDS["admin_user"],  # Reference to admin user
    # Test scenario IDs for the 11 chess positions (using large integers to avoid conflicts)
    "test_scenario_chess_1": 800000000000000001,
    "test_scenario_chess_2": 800000000000000002,
    "test_scenario_chess_3": 800000000000000003,
    "test_scenario_chess_4": 800000000000000004,
    "test_scenario_chess_5": 800000000000000005,
    "test_scenario_chess_6": 800000000000000006,
    "test_scenario_chess_7": 800000000000000007,
    "test_scenario_chess_8": 800000000000000008,
    "test_scenario_chess_9": 800000000000000009,
    "test_scenario_chess_10": 800000000000000010,
    "test_scenario_chess_11": 800000000000000011,
}

ADMIN_USER_ID: UserId = UserId(TSID(PREDEFINED_IDS["admin_user"]))

# Agent avatar filenames
AGENT_AVATARS: dict[str, str] = {
    "agent_poker": "gambit.png",  # Gambit - Texas Hold'em poker agent
    "agent_poker_2": "virgil.png",  # Virgil - Second poker bot
    "agent_poker_3": "norman.png",  # Norman - Third poker agent
    "agent_chess": "splinter.png",  # Splinter - Main chess agent
    "agent_chess_2": "shredder.png",  # Shredder - Second chess bot
    "agent_chess_stockfish": "Krang.png",  # Krang - Stockfish brain bot
}

# Predefined LLM Integration IDs (user_key + provider)
# Format: llm_{user_key}_{provider}
PREDEFINED_LLM_INTEGRATION_IDS: dict[str, int] = {
    # Admin user integrations
    "llm_admin_openai": 760447946411413761,
    "llm_admin_gemini": 760447946411413762,
    "llm_admin_anthropic": 760447946411413763,
    "llm_admin_aws_bedrock": 760447946411413764,
    # Ilia German integrations
    "llm_iliagerman_openai": 760447946411413765,
    "llm_iliagerman_gemini": 760447946411413766,
    "llm_iliagerman_anthropic": 760447946411413767,
    "llm_iliagerman_aws_bedrock": 760447946411413768,
    # Gil Pali integrations
    "llm_gilpali_openai": 760447946411413769,
    "llm_gilpali_gemini": 760447946411413770,
    "llm_gilpali_anthropic": 760447946411413771,
    "llm_gilpali_aws_bedrock": 760447946411413772,
}


# Helper function to get LLM integration ID
def get_llm_integration_id(user_key: str, provider: LLMProvider) -> int:
    """Get predefined LLM integration ID for a user and provider combination."""
    provider_suffix = provider.value.replace(".", "_")
    key = f"llm_{user_key}_{provider_suffix}"
    return PREDEFINED_LLM_INTEGRATION_IDS.get(key, TSID.create().number)


def generate_placeholder_avatar(filename: str) -> str:
    """Generate avatar URL path for serving from client.

    Returns a URL path that points to the avatar file served by the client.
    Avatar files should be located in client/public/avatars directory.

    Args:
        filename: The filename for the avatar (e.g., 'ilia.jpg', 'splinter.png')

    Returns:
        A URL path string for the avatar (e.g., '/avatars/splinter.png')
    """
    logger.info(
        f"Generated avatar URL for: {filename}",
        operation="generate_placeholder_avatar",
        filename=filename,
        url=f"/avatars/{filename}",
    )

    return f"/avatars/{filename}"


# Predefined chess FEN positions with meaningful names
CHESS_PRESET_POSITIONS: list[ChessPosition] = [
    {
        "name": "Complex Endgame - Knights vs Queen",
        "fen": "6kr/5p1p/4pPp1/2p1P3/2p1PQ2/4n2P/pp3nPK/7R w - - 0 1",
        "description": "White to move. Material imbalance with queen vs two knights. White has advanced pawns but Black's knights are active. Find the winning continuation.",
        "tags": ["endgame", "material-imbalance", "tactical"],
    },
    {
        "name": "Middlegame Attack - Piece Coordination",
        "fen": "r1b2r1k/4qp1p/p1Nppb1Q/4nP2/1p2P3/2N5/PPP4P/2KR1BR1 b - - 5 18",
        "description": "Black to move. Material equal. White has strong piece coordination with knights on c3/c6 and queen on h6. Black must defend accurately.",
        "tags": ["middlegame", "attack", "defense"],
    },
    {
        "name": "Rook Endgame - Active Pieces",
        "fen": "8/pR4pk/1b2p3/2p3p1/N1p5/7P/Pr4P1/6K1 w - - 0 32",
        "description": "White to move. White is down material but has an active rook on b7. Black's rook on b2 is also active. Precise calculation required.",
        "tags": ["endgame", "rook-endgame", "active-pieces"],
    },
    {
        "name": "Forced Defense - King in Check",
        "fen": "rn3rk1/pbppq1pQ/1p2pb2/4N3/3PN3/3B4/PPP2PPP/R3K2R b KQ - 0 11",
        "description": "Black to move. Black king is in check from White's queen on h7. Only one legal move available. Critical defensive position.",
        "tags": ["middlegame", "check", "forced-move", "defense"],
    },
    {
        "name": "Bishop Endgame - Pawn Race",
        "fen": "8/B7/7P/4p3/3b3k/8/8/2K5 b - - 1 1",
        "description": "Black to move. Opposite-colored bishops with passed pawns. Both sides race to promote. Calculate the pawn race accurately.",
        "tags": ["endgame", "bishop-endgame", "pawn-race"],
    },
    {
        "name": "Desperate Defense - King in Check",
        "fen": "r4rkQ/pp2pp1p/3p2p1/6B1/7P/1P6/1RPKnPP1/q6R b - - 1 1",
        "description": "Black to move. Black king in check from White's queen on h8. Material roughly equal but Black's position is critical. Find the only defense.",
        "tags": ["middlegame", "check", "forced-move", "tactical"],
    },
    {
        "name": "Rook Endgame - Passed Pawns",
        "fen": "8/6kp/6p1/4p3/p3rPRP/3K2P1/8/8 w - - 2 44",
        "description": "White to move. Rook and pawn endgame with passed pawns on both sides. White's rook is active on h4. Technique and calculation required.",
        "tags": ["endgame", "rook-endgame", "passed-pawns"],
    },
    {
        "name": "Tactical Chaos - Promotion Threats",
        "fen": "r4k1r/1b2bPR1/p4n1B/3p4/4P2P/1q5B/PpP5/1K4R1 b - - 1 26",
        "description": "Black to move. Material equal. White has a far-advanced pawn on f7 threatening promotion. Black has a dangerous passed pawn on b2. Complex tactics.",
        "tags": ["middlegame", "tactical", "promotion", "passed-pawns"],
    },
    {
        "name": "Queen and Rook Attack",
        "fen": "5rk1/pp4pp/4p3/2R3Q1/3n4/6qr/P1P2PPP/5RK1 w - - 2 24",
        "description": "White to move. Material roughly equal. Both sides have queen and rook. White's pieces are more active with rook on c5 and queen on g5. Find the best continuation.",
        "tags": ["middlegame", "attack", "queen-and-rook"],
    },
    {
        "name": "Complex Middlegame - Multiple Threats",
        "fen": "2rq2kb/pbQr3p/2n1R1pB/1pp2pN1/3p4/P1PP2P1/1P3PBP/4R1K1 b - - 1 1",
        "description": "Black to move. Material equal. White has queen on c7 and rook on e6 creating threats. Black must coordinate defense with multiple pieces.",
        "tags": ["middlegame", "tactical", "complex"],
    },
    {
        "name": "Bishop Endgame - Opposite Colors",
        "fen": "8/8/4kpp1/3p4/p6P/2B4b/6P1/6K1 w - - 1 48",
        "description": "White to move. Opposite-colored bishops. White is down material but opposite-colored bishop endgames are often drawn. Find the drawing technique.",
        "tags": ["endgame", "bishop-endgame", "opposite-bishops", "drawing"],
    },
]


def convert_fen_to_chess_state(fen: str) -> dict[str, Any]:
    """Convert FEN string to chess game state format."""
    board = chess.Board(fen)

    # Convert board to 8x8 matrix
    board_matrix: list[list[dict[str, str] | None]] = []
    for rank in range(7, -1, -1):  # Start from rank 8 down to rank 1
        row: list[dict[str, str] | None] = []
        for file in range(8):  # Files a-h
            square = chess.square(file, rank)
            piece = board.piece_at(square)
            if piece:
                piece_type = piece.symbol().lower()
                # Map chess piece symbols to full names
                piece_map = {"p": "pawn", "n": "knight", "b": "bishop", "r": "rook", "q": "queen", "k": "king"}
                row.append({"type": piece_map[piece_type], "color": "white" if piece.color == chess.WHITE else "black"})
            else:
                row.append(None)
        board_matrix.append(row)

    return {
        "board": board_matrix,
        "side_to_move": "white" if board.turn == chess.WHITE else "black",
        "castling_rights": {
            "white_kingside": board.has_kingside_castling_rights(chess.WHITE),
            "white_queenside": board.has_queenside_castling_rights(chess.WHITE),
            "black_kingside": board.has_kingside_castling_rights(chess.BLACK),
            "black_queenside": board.has_queenside_castling_rights(chess.BLACK),
        },
        "en_passant_target": chess.square_name(board.ep_square) if board.ep_square else None,
        "halfmove_clock": board.halfmove_clock,
        "fullmove_number": board.fullmove_number,
    }


async def populate_db() -> bool | None:
    """Populate the database with system test scenarios, tools, agents, and LLM integrations."""
    global logger
    logger = get_logger(__name__)
    config_service = ConfigService()
    admin_email = config_service.get("populate_db.email")
    admin_password = config_service.get("populate_db.password")
    admin_cognito_sub = config_service.get("populate_db.cognito_sub")

    if not admin_email or not admin_password:
        logger.error(
            "Admin credentials not configured. Please set populate_db.email, populate_db.password, and populate_db.cognito_sub in your secrets.yaml",
            operation="populate_db",
            status="error",
        )
        return False

    async with AsyncSessionLocal() as db:
        try:
            # 1. Create or Update All Predefined Users
            logger.info("Creating/updating predefined users...", operation="populate_db")

            # Fetch all existing users by ID
            result = await db.execute(select(User).where(User.id.in_(list(PREDEFINED_USER_IDS.values()))))
            existing_users_by_id: dict[int, User] = {tsid_to_int(user.id): user for user in result.scalars().all()}

            # Also fetch by cognito_sub to handle cases where user exists with different ID
            cognito_subs = [data["cognito_sub"] for data in PREDEFINED_USERS.values()]
            result = await db.execute(select(User).where(User.cognito_sub.in_(cognito_subs)))
            existing_users_by_cognito: dict[str | None, User] = {user.cognito_sub: user for user in result.scalars().all()}

            admin_user = None
            for user_key, user_data in PREDEFINED_USERS.items():
                user_id: int = user_data["id"]

                # For admin user, use credentials from config
                if user_key == "admin_user":
                    email = admin_email
                    cognito_sub = admin_cognito_sub
                else:
                    email = user_data["email"]
                    cognito_sub = user_data["cognito_sub"]

                # Check if user exists by ID or cognito_sub
                existing_user = existing_users_by_id.get(user_id) or existing_users_by_cognito.get(cognito_sub)

                if not existing_user:
                    logger.info(
                        f"Creating user: {email}",
                        operation="populate_db",
                        user_id=user_id,
                    )
                    # Generate placeholder avatar
                    avatar_url = generate_placeholder_avatar(user_data["avatar_filename"])
                    new_user = User(
                        id=user_id,
                        username=user_data["username"],
                        email=email,
                        full_name=user_data["full_name"],
                        role=user_data["role"],
                        is_active=True,
                        cognito_sub=cognito_sub,
                        avatar_url=avatar_url,
                        avatar_type=AvatarType.UPLOADED,
                        coins_balance=1000000,  # System users start with 1 million tokens
                    )
                    db.add(new_user)
                    # Flush immediately to avoid batch insert issues with TSID type conversion
                    await db.flush()
                    if user_key == "admin_user":
                        admin_user = new_user
                    logger.info(
                        f"User created: {email} with 1,000,000 tokens",
                        operation="populate_db",
                        user_id=user_id,
                    )
                else:
                    logger.info(
                        f"User already exists, updating: {email}",
                        operation="populate_db",
                        user_id=user_id,
                    )
                    # Update existing user with latest data
                    existing_user.username = user_data["username"]
                    existing_user.email = email
                    existing_user.full_name = user_data["full_name"]
                    existing_user.role = user_data["role"]
                    existing_user.is_active = True
                    existing_user.cognito_sub = cognito_sub
                    # Always update avatar from file for predefined users
                    existing_user.avatar_url = generate_placeholder_avatar(user_data["avatar_filename"])
                    existing_user.avatar_type = AvatarType.UPLOADED
                    # Ensure system users have 1 million tokens
                    existing_user.coins_balance = 1000000
                    if user_key == "admin_user":
                        admin_user = existing_user

            if not admin_user:
                logger.error("Admin user not found after creation/update", operation="populate_db")
                return False
                admin_user.cognito_sub = admin_cognito_sub
                await db.flush()
                logger.info(
                    "Admin user updated successfully.",
                    operation="populate_db",
                    user_id=admin_user.id,
                )

            # 2. Create All Available LLM Integrations
            logger.info("Setting up LLM integrations...", operation="populate_db")

            # Check which API keys are available
            llm_configs: list[LLMConfig] = []

            # AWS Bedrock (priority 1 - displayed first)
            aws_bedrock_api_key = config_service.get("llm_providers.aws_bedrock.api_key")
            if aws_bedrock_api_key:
                llm_configs.append(
                    {
                        "provider": LLMProvider.AWS_BEDROCK,
                        "model": AWSBedrockModel.FAST.value,
                        "display_name": "AWS Bedrock",
                        "api_key": aws_bedrock_api_key,
                        "priority": 1,
                    }
                )
                logger.info("AWS Bedrock API key found", operation="populate_db")

            # Google Gemini (priority 2)
            gemini_api_key = config_service.get("llm_providers.gemini.api_key")
            if gemini_api_key:
                llm_configs.append(
                    {
                        "provider": LLMProvider.GOOGLE,
                        "model": GoogleModel.FAST.value,
                        "display_name": "Google Gemini",
                        "api_key": gemini_api_key,
                        "priority": 2,
                    }
                )
                logger.info("Google Gemini API key found", operation="populate_db")

            # OpenAI (priority 3 - fast model, default for agents)
            openai_api_key = config_service.get("llm_providers.openai.api_key")
            if openai_api_key:
                llm_configs.append(
                    {
                        "provider": LLMProvider.OPENAI,
                        "model": OpenAIModel.FAST.value,
                        "display_name": "OpenAI",
                        "api_key": openai_api_key,
                        "priority": 3,
                    }
                )
                logger.info("OpenAI API key found", operation="populate_db")

            # Anthropic (priority 4)
            anthropic_api_key = config_service.get("llm_providers.anthropic.api_key")
            if anthropic_api_key:
                llm_configs.append(
                    {
                        "provider": LLMProvider.ANTHROPIC,
                        "model": AnthropicModel.FAST.value,
                        "display_name": "Anthropic",
                        "api_key": anthropic_api_key,
                        "priority": 4,
                    }
                )
                logger.info("Anthropic API key found", operation="populate_db")

            if not llm_configs:
                logger.error(
                    "No LLM provider API keys found. Please configure at least one provider in your secrets.yaml",
                    operation="populate_db",
                    status="error",
                )
                return False

            # Sort by priority for display order
            llm_configs.sort(key=lambda x: x["priority"])

            # Use AWS Bedrock as default if available; otherwise choose a non-Google provider if possible
            default_provider = next(
                (config for config in llm_configs if config["provider"] == LLMProvider.AWS_BEDROCK),
                None,
            )
            if default_provider is None:
                default_provider = next(
                    (config for config in llm_configs if config["provider"] != LLMProvider.GOOGLE),
                    llm_configs[0],
                )

            logger.info(
                f"Using {default_provider['display_name']} as default provider for agents",
                operation="populate_db",
                provider=default_provider["provider"].value,
            )

            # Get all users that should have LLM integrations
            # Fetch ALL users from database (not just predefined ones)
            # This ensures that users who log in via OAuth also get LLM integrations
            result = await db.execute(select(User))
            existing_users: dict[int, User] = {tsid_to_int(user.id): user for user in result.scalars().all()}

            logger.info(
                f"Creating LLM integrations for {len(existing_users)} users",
                operation="populate_db",
                user_count=len(existing_users),
                user_emails=[user.email for user in existing_users.values()],
            )

            # Create a mapping from user_id to user_key for LLM integration ID lookup
            user_id_to_key: dict[int, str] = {}
            for user_key, user_data in PREDEFINED_USERS.items():
                user_id_to_key[user_data["id"]] = user_key

            # Create or update LLM integrations for all users
            created_integrations: dict[LLMProvider, LLMIntegration] = {}
            admin_user_db_id = admin_user.id
            admin_user_int_id = tsid_to_int(admin_user_db_id)
            logger.info(
                f"Admin user ID for comparison: {admin_user_int_id}",
                operation="populate_db",
                admin_user_id=admin_user_int_id,
                admin_user_id_type=type(admin_user_db_id).__name__,
            )
            for user_id_int, user in existing_users.items():
                user_id_value = user.id
                is_admin_user = tsid_to_int(user_id_value) == admin_user_int_id
                user_key = user_id_to_key.get(user_id_int, "unknown")
                logger.info(
                    f"Setting up LLM integrations for user: {user.email}",
                    operation="populate_db",
                    user_id=user_id_int,
                    user_key=user_key,
                    user_id_type=type(user_id_value).__name__,
                    email=user.email,
                    is_admin=is_admin_user,
                )

                # First, reset all existing integrations for this user to not be default
                # This ensures only one integration will be default after the update
                result = await db.execute(select(LLMIntegration).where(LLMIntegration.user_id == user_id_value))
                existing_user_integrations = result.scalars().all()
                for existing_int in existing_user_integrations:
                    existing_int.is_default = False
                await db.flush()

                for config in llm_configs:
                    result = await db.execute(
                        select(LLMIntegration).where(
                            LLMIntegration.user_id == user_id_value,
                            LLMIntegration.provider == config["provider"],
                        )
                    )
                    existing_integration = result.scalar_one_or_none()

                    # Encrypt API key using shared utility
                    encrypted_key = encrypt_api_key(config["api_key"])

                    is_default = config["provider"] == default_provider["provider"]

                    if existing_integration:
                        logger.info(
                            f"Updating existing {config['display_name']} integration for {user.email}",
                            operation="populate_db",
                            llm_id=existing_integration.id,
                            user_email=user.email,
                        )
                        existing_integration.api_key_encrypted = encrypted_key
                        existing_integration.selected_model = config["model"]
                        existing_integration.display_name = config["display_name"]
                        existing_integration.is_active = True
                        existing_integration.is_default = is_default
                        await db.flush()

                        # Store admin user's integrations for agent configuration
                        if is_admin_user:
                            created_integrations[config["provider"]] = existing_integration
                    else:
                        # Get predefined ID for this user and provider
                        integration_id = get_llm_integration_id(user_key, config["provider"])
                        logger.info(
                            f"Creating new {config['display_name']} integration for {user.email}",
                            operation="populate_db",
                            user_email=user.email,
                            integration_id=integration_id,
                        )
                        new_integration = LLMIntegration(
                            id=integration_id,
                            user_id=user_id_value,
                            provider=config["provider"],
                            api_key_encrypted=encrypted_key,
                            selected_model=config["model"],
                            display_name=config["display_name"],
                            is_active=True,
                            is_default=is_default,
                        )
                        db.add(new_integration)
                        await db.flush()

                        # Store admin user's integrations for agent configuration
                        if is_admin_user:
                            created_integrations[config["provider"]] = new_integration

                        logger.info(
                            f"{config['display_name']} integration created for {user.email}",
                            operation="populate_db",
                            llm_id=new_integration.id,
                            user_email=user.email,
                        )

            # Get the default integration for agent configuration (from admin user)
            if default_provider["provider"] not in created_integrations:
                logger.error(
                    f"Default provider {default_provider['display_name']} not found in created integrations",
                    operation="populate_db",
                    provider=default_provider["provider"].value,
                    available_providers=[p.value for p in created_integrations],
                )
                return False
            default_integration = created_integrations[default_provider["provider"]]

            # 3. Create or Update Attack Detector Tool
            logger.info("Setting up Attack Detector tool...", operation="populate_db")
            result = await db.execute(select(Tool).where(Tool.id == PREDEFINED_IDS["tool_attack_detector"]))
            existing_attack_detector = result.scalar_one_or_none()

            attack_detector_code = '''def lambda_handler(event, context):
    """
    Analyze pieces under threat in the current chess position.

    Identifies and reports pieces that are currently under attack, organized by color
    and showing attacking pieces.

    Parameters: None

    Returns:
    - white_pieces_under_attack: List of white pieces being attacked
    - black_pieces_under_attack: List of black pieces being attacked
    - attack_summary: Human-readable description of threats
    """
    import json

    try:
        # Extract board from context
        body = event.get('body', {})
        if isinstance(body, str):
            body = json.loads(body)

        context_data = body.get('context', {})
        state = context_data.get('state', {})
        board = state.get('board')

        if not board:
            return {"error": "Missing board in context.state"}

        # Validate board structure - should be a dict mapping squares to pieces
        if not isinstance(board, dict):
            return {"error": "Invalid board format. Expected dict"}

        # Helper function to convert square notation to board coordinates
        def square_to_coords(square):
            """Convert square notation (e.g., 'a1', 'e4') to board coordinates (row, col)"""
            if len(square) != 2:
                return None
            file = square[0].lower()
            rank = square[1]
            if file < 'a' or file > 'h' or rank < '1' or rank > '8':
                return None
            col = ord(file) - ord('a')
            row = 8 - int(rank)
            return row, col

        # Helper function to check if a square is attacked
        def is_square_attacked(square, by_color):
            """Check if a square is attacked by pieces of given color"""
            attackers = []
            target_row, target_col = square_to_coords(square)
            if target_row is None:
                return attackers

            # Check all pieces of the attacking color
            for sq, piece in board.items():
                if piece.get('color') == by_color:
                    piece_type = piece.get('type')
                    piece_row, piece_col = square_to_coords(sq)
                    if piece_row is None:
                        continue

                    # Check if this piece can attack the target square
                    if piece_type == 'pawn':
                        # Pawns attack diagonally forward
                        # White pawns move up (decreasing row), black pawns move down (increasing row)
                        pawn_dir = -1 if by_color == 'white' else 1
                        if abs(piece_col - target_col) == 1 and target_row == piece_row + pawn_dir:
                            attackers.append({'type': 'pawn', 'position': sq})

                    elif piece_type == 'knight':
                        # Knight moves in L-shape
                        knight_moves = [(-2,-1), (-2,1), (-1,-2), (-1,2), (1,-2), (1,2), (2,-1), (2,1)]
                        for dr, dc in knight_moves:
                            if target_row == piece_row + dr and target_col == piece_col + dc:
                                attackers.append({'type': 'knight', 'position': sq})

                    elif piece_type == 'king':
                        # King moves one square in any direction
                        if abs(target_row - piece_row) <= 1 and abs(target_col - piece_col) <= 1:
                            if target_row != piece_row or target_col != piece_col:
                                attackers.append({'type': 'king', 'position': sq})

                    elif piece_type in ['rook', 'bishop', 'queen']:
                        # Sliding pieces
                        directions = {
                            'rook': [(0,1), (0,-1), (1,0), (-1,0)],
                            'bishop': [(1,1), (1,-1), (-1,1), (-1,-1)],
                            'queen': [(0,1), (0,-1), (1,0), (-1,0), (1,1), (1,-1), (-1,1), (-1,-1)]
                        }
                        dirs = directions.get(piece_type, [])

                        for dr, dc in dirs:
                            r, c = piece_row + dr, piece_col + dc
                            while 0 <= r < 8 and 0 <= c < 8:
                                if r == target_row and c == target_col:
                                    attackers.append({'type': piece_type, 'position': sq})
                                    break
                                # Check if there's a piece blocking the path
                                blocking_square = f"{chr(ord('a') + c)}{8 - r}"
                                if blocking_square in board:
                                    # Path is blocked, cannot attack through pieces
                                    break
                                r, c = r + dr, c + dc

            return attackers

        # Find all pieces under attack
        white_under_attack = []
        black_under_attack = []

        for square, piece in board.items():
            piece_type = piece.get('type')
            piece_color = piece.get('color')

            # Check if this piece is attacked by opponent
            opponent_color = 'black' if piece_color == 'white' else 'white'
            attackers = is_square_attacked(square, opponent_color)

            if attackers:
                attack_info = {
                    'piece': piece_type,
                    'position': square,
                    'attacked_by': attackers
                }
                if piece_color == 'white':
                    white_under_attack.append(attack_info)
                else:
                    black_under_attack.append(attack_info)

        # Generate summary
        summary_parts = []
        if white_under_attack:
            summary_parts.append(f"{len(white_under_attack)} white piece(s) under attack")
        if black_under_attack:
            summary_parts.append(f"{len(black_under_attack)} black piece(s) under attack")

        attack_summary = "; ".join(summary_parts) if summary_parts else "No pieces under attack"

        return {
            "white_pieces_under_attack": white_under_attack,
            "black_pieces_under_attack": black_under_attack,
            "attack_summary": attack_summary
        }

    except Exception as e:
        return {"error": f"Tool execution failed: {str(e)}"}
'''

            attack_detector_description = """Analyze pieces under threat in the current chess position.

Identifies and reports pieces that are currently under attack, organized by color
and showing attacking pieces.

Parameters: None

Returns:
- white_pieces_under_attack: List of white pieces being attacked
- black_pieces_under_attack: List of black pieces being attacked
- attack_summary: Human-readable description of threats

Usage Examples:
- Example 1: Identify all white pieces under attack
- Example 2: Find which pieces are attacking the black queen
- Example 3: Detect undefended pieces that can be captured

Key capabilities:
1. Comprehensive threat analysis
2. Identifies all attacking pieces
3. Organized by piece color
4. Robust input validation
5. Error handling for malformed inputs

The tool is particularly useful for:
- Chess AI tactical analysis
- Move validation and safety checks
- Threat assessment
- Defensive planning"""

            if existing_attack_detector:
                logger.info("Updating existing Attack Detector tool", operation="populate_db")
                existing_attack_detector.user_id = None
                existing_attack_detector.name = "attack_detector"
                existing_attack_detector.display_name = "Attack Detector"
                existing_attack_detector.description = attack_detector_description
                existing_attack_detector.code = attack_detector_code
                existing_attack_detector.environment = GameType.CHESS
                existing_attack_detector.validation_status = ToolValidationStatus.VALID
                existing_attack_detector.is_system = True
                await db.flush()
            else:
                logger.info("Creating Attack Detector tool", operation="populate_db")
                new_tool = Tool(
                    id=PREDEFINED_IDS["tool_attack_detector"],
                    user_id=None,
                    name="attack_detector",
                    display_name="Attack Detector",
                    description=attack_detector_description,
                    code=attack_detector_code,
                    environment=GameType.CHESS,
                    validation_status=ToolValidationStatus.VALID,
                    is_system=True,
                )
                db.add(new_tool)
                await db.flush()
                logger.info("Attack Detector tool created", operation="populate_db")

            # Store tool ID for later assignment
            additional_chess_tools = {PREDEFINED_IDS["tool_attack_detector"]: True}

            # 3.3. Create or Update Check Protected Tool
            logger.info("Setting up Check Protected tool...", operation="populate_db")
            result = await db.execute(select(Tool).where(Tool.id == PREDEFINED_IDS["tool_check_protected"]))
            existing_check_protected = result.scalar_one_or_none()

            check_protected_code = '''def lambda_handler(event, context):
    """
    Identify if a specific chess piece is protected.

    Determines whether a given piece is defended by other friendly pieces,
    preventing it from being captured without consequence.

    Parameters:
    - position (required): Position to check in algebraic notation (e.g., "e4")

    Returns:
    - is_protected: Boolean indicating if the piece is protected
    - defenders: List of friendly pieces defending this position
    - protection_summary: Human-readable description
    """
    import json

    try:
        # Extract parameters from event
        body = event.get('body', {})
        if isinstance(body, str):
            body = json.loads(body)

        context_data = body.get('context', {})
        state = context_data.get('state', {})
        board = state.get('board')

        position = body.get('position')

        if not board:
            return {"error": "Missing board in context.state"}
        if not position:
            return {"error": "Missing required parameter 'position'"}

        # Validate board structure - should be a dict mapping squares to pieces
        if not isinstance(board, dict):
            return {"error": "Invalid board format. Expected dict"}

        # Validate position format
        if len(position) != 2 or position[0].lower() < 'a' or position[0].lower() > 'h' or position[1] < '1' or position[1] > '8':
            return {"error": f"Invalid position format: {position}"}

        # Get the piece at the position
        target_piece = board.get(position)
        if not target_piece:
            return {
                "is_protected": False,
                "defenders": [],
                "protection_summary": f"No piece at {position}"
            }

        piece_color = target_piece.get('color')

        # Helper function to convert square notation to board coordinates
        def square_to_coords(square):
            """Convert square notation (e.g., 'a1', 'e4') to board coordinates (row, col)"""
            if len(square) != 2:
                return None
            file = square[0].lower()
            rank = square[1]
            if file < 'a' or file > 'h' or rank < '1' or rank > '8':
                return None
            col = ord(file) - ord('a')
            row = 8 - int(rank)
            return row, col

        # Helper function to check if a square is defended by friendly pieces
        def get_defenders(target_square, friendly_color):
            """Find all friendly pieces defending a square"""
            defenders = []
            target_row, target_col = square_to_coords(target_square)
            if target_row is None:
                return defenders

            # Check all pieces of the friendly color
            for sq, piece in board.items():
                if sq == target_square:  # Skip the target piece itself
                    continue
                if piece.get('color') == friendly_color:
                    piece_type = piece.get('type')
                    piece_row, piece_col = square_to_coords(sq)
                    if piece_row is None:
                        continue

                    # Check if this piece can defend the target square
                    if piece_type == 'pawn':
                        # Pawns defend diagonally (same as attack pattern)
                        # White pawns move up (decreasing row), black pawns move down (increasing row)
                        pawn_dir = -1 if friendly_color == 'white' else 1
                        if abs(piece_col - target_col) == 1 and target_row == piece_row + pawn_dir:
                            defenders.append({'type': 'pawn', 'position': sq})

                    elif piece_type == 'knight':
                        # Knight moves in L-shape
                        knight_moves = [(-2,-1), (-2,1), (-1,-2), (-1,2), (1,-2), (1,2), (2,-1), (2,1)]
                        for dr, dc in knight_moves:
                            if target_row == piece_row + dr and target_col == piece_col + dc:
                                defenders.append({'type': 'knight', 'position': sq})

                    elif piece_type == 'king':
                        # King moves one square in any direction
                        if abs(target_row - piece_row) <= 1 and abs(target_col - piece_col) <= 1:
                            defenders.append({'type': 'king', 'position': sq})

                    elif piece_type in ['rook', 'bishop', 'queen']:
                        # Sliding pieces
                        directions = {
                            'rook': [(0,1), (0,-1), (1,0), (-1,0)],
                            'bishop': [(1,1), (1,-1), (-1,1), (-1,-1)],
                            'queen': [(0,1), (0,-1), (1,0), (-1,0), (1,1), (1,-1), (-1,1), (-1,-1)]
                        }
                        dirs = directions.get(piece_type, [])

                        for dr, dc in dirs:
                            r, c = piece_row + dr, piece_col + dc
                            while 0 <= r < 8 and 0 <= c < 8:
                                if r == target_row and c == target_col:
                                    defenders.append({'type': piece_type, 'position': sq})
                                    break
                                # Check if there's a piece blocking the path
                                blocking_square = f"{chr(ord('a') + c)}{8 - r}"
                                if blocking_square in board:
                                    # Path is blocked, cannot defend through pieces
                                    break
                                r, c = r + dr, c + dc

            return defenders

        # Find defenders
        defenders = get_defenders(position, piece_color)
        is_protected = len(defenders) > 0

        # Generate summary
        if is_protected:
            defender_types = [d['type'] for d in defenders]
            protection_summary = f"{target_piece.get('type')} at {position} is protected by {len(defenders)} piece(s): {', '.join(defender_types)}"
        else:
            protection_summary = f"{target_piece.get('type')} at {position} is NOT protected"

        return {
            "is_protected": is_protected,
            "defenders": defenders,
            "protection_summary": protection_summary
        }

    except Exception as e:
        return {"error": f"Tool execution failed: {str(e)}"}
'''

            check_protected_description = """Identify if a specific chess piece is protected.

Determines whether a given piece is defended by other friendly pieces,
preventing it from being captured without consequence.

Parameters:
- position (required): Position to check in algebraic notation (e.g., "e4")

Returns:
- is_protected: Boolean indicating if the piece is protected
- defenders: List of friendly pieces defending this position
- protection_summary: Human-readable description

Usage Examples:
- Example 1: Check if the queen at e4 is protected
- Example 2: Verify if a pawn push is safe
- Example 3: Determine if a piece can be safely captured

Key capabilities:
1. Identifies all defending pieces
2. Works for any piece type
3. Considers all piece movement patterns
4. Provides detailed protection analysis
5. Robust input validation

The tool is particularly useful for:
- Chess AI tactical decisions
- Capture safety analysis
- Defensive planning
- Move validation"""

            if existing_check_protected:
                logger.info("Updating existing Check Protected tool", operation="populate_db")
                existing_check_protected.user_id = None
                existing_check_protected.name = "check_protected"
                existing_check_protected.display_name = "Check Protected"
                existing_check_protected.description = check_protected_description
                existing_check_protected.code = check_protected_code
                existing_check_protected.environment = GameType.CHESS
                existing_check_protected.validation_status = ToolValidationStatus.VALID
                existing_check_protected.is_system = True
                await db.flush()
            else:
                logger.info("Creating Check Protected tool", operation="populate_db")
                new_tool = Tool(
                    id=PREDEFINED_IDS["tool_check_protected"],
                    user_id=None,
                    name="check_protected",
                    display_name="Check Protected",
                    description=check_protected_description,
                    code=check_protected_code,
                    environment=GameType.CHESS,
                    validation_status=ToolValidationStatus.VALID,
                    is_system=True,
                )
                db.add(new_tool)
                await db.flush()
                logger.info("Check Protected tool created", operation="populate_db")

            # Store both tool IDs for later assignment
            additional_chess_tools[PREDEFINED_IDS["tool_check_protected"]] = True

            # 3.4. Query and Update Move Validator Tool
            logger.info("Querying Move Validator tool from database...", operation="populate_db")
            result = await db.execute(select(Tool).where(Tool.id == PREDEFINED_IDS["tool_move_validator"]))
            move_validator_tool = result.scalar_one_or_none()

            if move_validator_tool:
                logger.info("Updating Move Validator tool to system status", operation="populate_db")
                move_validator_tool.user_id = None  # System tools have no user
                move_validator_tool.is_system = True
                move_validator_tool.validation_status = ToolValidationStatus.VALID
                await db.flush()
                additional_chess_tools[PREDEFINED_IDS["tool_move_validator"]] = True
            else:
                logger.warning("Move Validator tool not found in database", operation="populate_db")

            # 3.5. Create or Update Poker Hand Evaluator Tool
            logger.info("Setting up poker hand evaluator tool...", operation="populate_db")
            result = await db.execute(select(Tool).where(Tool.id == PREDEFINED_IDS["tool_poker_hand_evaluator"]))
            existing_poker_tool = result.scalar_one_or_none()

            poker_tool_code = '''def lambda_handler(event, context):
    """
    Evaluate Texas Hold'em poker hands and determine winning hands.

    This tool helps poker agents understand hand strength by evaluating
    hole cards, community cards, and determining the best possible hand.

    Parameters:
    - hole_cards (required): List of 2 hole cards (format: [{'rank': 'A', 'suit': '♠'}, ...])
    - community_cards (required): List of community cards (0-5 cards)
    - num_players (optional): Number of players in the hand (default: 2)

    Returns:
    - hand_rank: Poker hand rank (High Card, Pair, Two Pair, Three of a Kind, Straight, Flush, Full House, Four of a Kind, Straight Flush, Royal Flush)
    - hand_description: Human-readable description of the hand
    - hand_strength: Numeric strength value (higher is better)
    - best_five_cards: The best 5-card combination
    - odds: Basic odds information
    """
    import json

    try:
        # Extract parameters
        body = event.get('body', {})
        if isinstance(body, str):
            body = json.loads(body)

        hole_cards = body.get('hole_cards')
        community_cards = body.get('community_cards', [])
        num_players = body.get('num_players', 2)

        # Validate inputs
        if not hole_cards or len(hole_cards) != 2:
            return {
                "error": "Exactly 2 hole cards are required."
            }

        if not isinstance(community_cards, list) or len(community_cards) > 5:
            return {
                "error": "Community cards must be a list of 0-5 cards."
            }

        # Card values and suits
        ranks = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
        suits = ['♠', '♥', '♦', '♣']

        # Create all available cards (hole + community)
        all_cards = hole_cards + community_cards

        if len(all_cards) < 2:
            return {
                "error": "At least 2 cards are required for evaluation."
            }

        # Simple hand evaluation (basic implementation)
        def evaluate_hand(cards):
            """Simple poker hand evaluation"""
            rank_counts = {}
            suit_counts = {}

            for card in cards:
                rank = card.get('rank', '')
                suit = card.get('suit', '')

                rank_counts[rank] = rank_counts.get(rank, 0) + 1
                suit_counts[suit] = suit_counts.get(suit, 0) + 1

            # Check for different hand types
            is_flush = any(count >= 5 for count in suit_counts.values())

            # Check for pairs, three of a kind, four of a kind
            pairs = []
            three_of_kind = []
            four_of_kind = []

            for rank, count in rank_counts.items():
                if count == 2:
                    pairs.append(rank)
                elif count == 3:
                    three_of_kind.append(rank)
                elif count == 4:
                    four_of_kind.append(rank)

            # Determine hand rank
            if four_of_kind:
                return {"rank": "Four of a Kind", "strength": 8, "cards": four_of_kind}
            elif three_of_kind and pairs:
                return {"rank": "Full House", "strength": 7, "cards": three_of_kind + pairs}
            elif is_flush:
                return {"rank": "Flush", "strength": 6, "cards": []}
            elif len(three_of_kind) > 0:
                return {"rank": "Three of a Kind", "strength": 4, "cards": three_of_kind}
            elif len(pairs) >= 2:
                return {"rank": "Two Pair", "strength": 3, "cards": pairs}
            elif len(pairs) == 1:
                return {"rank": "Pair", "strength": 2, "cards": pairs}
            else:
                # High card - find the highest card
                high_card = max(cards, key=lambda x: ranks.index(x.get('rank', '2')) if x.get('rank') in ranks else 0)
                return {"rank": "High Card", "strength": 1, "cards": [high_card.get('rank')]}

        # Evaluate current hand
        if len(all_cards) >= 5:
            # Use best 5 cards
            hand_result = evaluate_hand(all_cards[:5])
        else:
            hand_result = evaluate_hand(all_cards)

        # Generate hand description
        hand_description = f"{hand_result['rank']} with {len(all_cards)} cards"

        # Basic odds calculation (simplified)
        if len(community_cards) == 0:  # Pre-flop
            odds_info = "Pre-flop: Random hand"
        elif len(community_cards) == 3:  # Flop
            odds_info = "Post-flop: 2 cards to come"
        elif len(community_cards) == 4:  # Turn
            odds_info = "Post-turn: 1 card to come"
        else:  # River
            odds_info = "Post-river: Final hand"

        return {
            "hand_rank": hand_result['rank'],
            "hand_description": hand_description,
            "hand_strength": hand_result['strength'],
            "best_five_cards": all_cards[:5] if len(all_cards) >= 5 else all_cards,
            "hole_cards": hole_cards,
            "community_cards": community_cards,
            "num_players": num_players,
            "odds_info": odds_info,
            "cards_evaluated": len(all_cards)
        }

    except json.JSONDecodeError as e:
        return {
            "error": f"Invalid JSON in request body: {str(e)}"
        }
    except Exception as e:
        return {
            "error": f"Unexpected error: {str(e)}"
        }'''

            poker_tool_description = """Evaluate Texas Hold'em poker hands and determine winning hands.

This tool helps poker agents understand hand strength by evaluating
hole cards, community cards, and determining the best possible hand.

Parameters:
- hole_cards (required): List of 2 hole cards (format: [{'rank': 'A', 'suit': '♠'}, ...])
- community_cards (required): List of community cards (0-5 cards)
- num_players (optional): Number of players in the hand (default: 2)

Returns:
- hand_rank: Poker hand rank (High Card, Pair, Two Pair, Three of a Kind, Straight, Flush, Full House, Four of a Kind, Straight Flush, Royal Flush)
- hand_description: Human-readable description of the hand
- hand_strength: Numeric strength value (higher is better)
- best_five_cards: The best 5-card combination
- odds: Basic odds information

### Human-Readable Description
This AWS Lambda function serves as a comprehensive poker hand evaluation tool designed for Texas Hold'em AI agents. It analyzes hole cards and community cards to determine hand strength, identify winning combinations, and provide basic odds information. The tool evaluates poker hands according to standard poker rankings and returns structured data about hand composition, strength ratings, and situational context.

### OpenAPI Schema
```yaml
components:
  schemas:
    ToolParams:
      type: object
      properties:
        hole_cards:
          type: array
          description: Array of 2 hole cards
          minItems: 2
          maxItems: 2
          items:
            type: object
            properties:
              rank:
                type: string
                enum: ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
              suit:
                type: string
                enum: ['♠', '♥', '♦', '♣']
          required: ['rank', 'suit']
        community_cards:
          type: array
          description: Array of community cards (0-5 cards)
          maxItems: 5
          items:
            type: object
            properties:
              rank:
                type: string
                enum: ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
              suit:
                type: string
                enum: ['♠', '♥', '♦', '♣']
            required: ['rank', 'suit']
        num_players:
          type: integer
          description: Number of players in the hand
          minimum: 2
          maximum: 10
          default: 2
      required: ['hole_cards']
```

### Usage Examples
```json
{
  "body": {
    "hole_cards": [
      {"rank": "A", "suit": "♠"},
      {"rank": "K", "suit": "♠"}
    ],
    "community_cards": [
      {"rank": "Q", "suit": "♠"},
      {"rank": "J", "suit": "♠"},
      {"rank": "10", "suit": "♠"}
    ],
    "num_players": 4
  }
}
```

Key capabilities of this tool:
1. Standard poker hand evaluation
2. Multiple hand type detection (pairs, straights, flushes, etc.)
3. Hand strength ranking
4. Basic odds calculation
5. Support for all game stages (pre-flop, flop, turn, river)
6. Error handling for invalid inputs

The tool is particularly useful for:
- Texas Hold'em AI agents
- Poker strategy analysis
- Hand strength assessment
- Pot odds calculation
- Game decision support

The function performs multiple key tasks:
- Validates card inputs
- Evaluates hand rankings
- Provides strength metrics
- Calculates basic odds information
- Returns structured data for AI processing"""

            if existing_poker_tool:
                logger.info("Updating existing poker hand evaluator tool", operation="populate_db")
                existing_poker_tool.user_id = None  # System tool
                existing_poker_tool.name = "texas_hand_evaluator"
                existing_poker_tool.display_name = "Texas Hold'em Hand Evaluator"
                existing_poker_tool.description = poker_tool_description
                existing_poker_tool.code = poker_tool_code
                existing_poker_tool.environment = GameType.TEXAS_HOLDEM
                existing_poker_tool.validation_status = ToolValidationStatus.VALID
                existing_poker_tool.is_system = True
                await db.flush()
            else:
                logger.info("Creating poker hand evaluator tool", operation="populate_db")
                new_poker_tool = Tool(
                    id=PREDEFINED_IDS["tool_poker_hand_evaluator"],
                    user_id=PREDEFINED_IDS["admin_user"],  # System tool owned by admin
                    name="texas_hand_evaluator",
                    display_name="Texas Hold'em Hand Evaluator",
                    description=poker_tool_description,
                    code=poker_tool_code,
                    environment=GameType.TEXAS_HOLDEM,
                    validation_status=ToolValidationStatus.VALID,
                    is_system=True,
                )
                db.add(new_poker_tool)
                await db.flush()
                logger.info("Poker hand evaluator tool created", operation="populate_db")

            # 4. Create or Update Agents with predefined IDs
            logger.info("Setting up agents...", operation="populate_db")

            # Poker Agent
            result = await db.execute(select(Agent).where(Agent.id == PREDEFINED_IDS["agent_poker"]))
            poker_agent = result.scalar_one_or_none()

            if not poker_agent:
                logger.info("Creating Gambit agent", operation="populate_db")
                avatar_url = generate_placeholder_avatar(AGENT_AVATARS["agent_poker"])
                poker_agent = Agent(
                    id=PREDEFINED_IDS["agent_poker"],
                    user_id=PREDEFINED_IDS["admin_user"],  # System agent owned by admin
                    name="Gambit",
                    description="An AI agent designed to play Texas Hold'em poker with style and flair.",
                    game_environment=GameType.TEXAS_HOLDEM,
                    auto_buy=True,
                    is_active=True,
                    is_system=True,
                    avatar_url=avatar_url,
                    avatar_type=AvatarType.UPLOADED,
                )
                db.add(poker_agent)
                await db.flush()
            else:
                logger.info("Updating Gambit agent", operation="populate_db")
                poker_agent.user_id = ADMIN_USER_ID  # System agent owned by admin
                poker_agent.name = "Gambit"
                poker_agent.description = "An AI agent designed to play Texas Hold'em poker with style and flair."
                poker_agent.game_environment = GameType.TEXAS_HOLDEM
                poker_agent.auto_buy = True
                poker_agent.is_active = True
                poker_agent.is_system = True
                # Always update avatar from file for system agents
                poker_agent.avatar_url = generate_placeholder_avatar(AGENT_AVATARS["agent_poker"])
                poker_agent.avatar_type = AvatarType.UPLOADED
                await db.flush()

            # Poker Agent Version
            result = await db.execute(select(AgentVersion).where(AgentVersion.id == PREDEFINED_IDS["agent_version_poker"]))
            poker_version = result.scalar_one_or_none()

            if not poker_version:
                logger.info("Creating Texas Hold'em agent version", operation="populate_db")
                poker_version = AgentVersion(
                    id=PREDEFINED_IDS["agent_version_poker"],
                    agent_id=poker_agent.id,
                    user_id=admin_user.id,
                    version_number=1,
                    system_prompt="You are an expert Texas Hold'em poker player. Analyze the game state and make optimal decisions based on your cards, community cards, pot odds, and opponent behavior.",
                    conversation_instructions="You are Gambit, the charming card-throwing mutant from X-Men. Speak with Cajun flair and confidence. Use card and game metaphors. Be smooth, calculated, and always seem to have an ace up your sleeve. Mon ami, the cards, they never lie.",
                    exit_criteria="Stop when the game ends or when you've made your final decision for the current hand.",
                    slow_llm_provider=default_provider["provider"].value,
                    slow_llm_model=default_integration.selected_model,
                    fast_llm_provider=default_provider["provider"].value,
                    fast_llm_model=default_integration.selected_model,
                    timeout=300,
                    max_iterations=10,
                    is_active=True,
                )
                db.add(poker_version)
                await db.flush()
            else:
                logger.info("Updating Texas Hold'em agent version", operation="populate_db")
                poker_version.system_prompt = "You are an expert Texas Hold'em poker player. Analyze the game state and make optimal decisions based on your cards, community cards, pot odds, and opponent behavior."
                poker_version.conversation_instructions = "You are Gambit, the charming card-throwing mutant from X-Men. Speak with Cajun flair and confidence. Use card and game metaphors. Be smooth, calculated, and always seem to have an ace up your sleeve. Mon ami, the cards, they never lie."
                poker_version.exit_criteria = "Stop when the game ends or when you've made your final decision for the current hand."
                poker_version.slow_llm_provider = default_provider["provider"].value
                poker_version.slow_llm_model = default_integration.selected_model
                poker_version.fast_llm_provider = default_provider["provider"].value
                poker_version.fast_llm_model = default_integration.selected_model
                poker_version.timeout = 300
                poker_version.max_iterations = 10
                poker_version.is_active = True
                await db.flush()

            # Create hidden opponent poker agent (clone for matchmaking, only visible to admin)
            result = await db.execute(select(Agent).where(Agent.id == PREDEFINED_IDS["agent_poker_2"]))
            poker_agent_2 = result.scalar_one_or_none()

            if not poker_agent_2:
                logger.info("Creating hidden Poker opponent agent (Virgil)", operation="populate_db")
                avatar_url = generate_placeholder_avatar(AGENT_AVATARS["agent_poker_2"])
                poker_agent_2 = Agent(
                    id=PREDEFINED_IDS["agent_poker_2"],
                    user_id=PREDEFINED_IDS["admin_user"],  # Owned by admin, used for matchmaking
                    name="Virgil",
                    description="Opponent agent for matchmaking (admin only). The wise owl from Mighty Max.",
                    game_environment=GameType.TEXAS_HOLDEM,
                    auto_buy=True,
                    is_active=True,
                    is_system=False,  # Regular agent, not system
                    avatar_url=avatar_url,
                    avatar_type=AvatarType.UPLOADED,
                )
                db.add(poker_agent_2)
                await db.flush()
            else:
                logger.info("Updating hidden Poker opponent agent (Virgil)", operation="populate_db")
                poker_agent_2.user_id = ADMIN_USER_ID
                poker_agent_2.name = "Virgil"
                poker_agent_2.description = "Opponent agent for matchmaking (admin only). The wise owl from Mighty Max."
                poker_agent_2.game_environment = GameType.TEXAS_HOLDEM
                poker_agent_2.auto_buy = True
                poker_agent_2.is_active = True
                poker_agent_2.is_system = False
                poker_agent_2.avatar_url = generate_placeholder_avatar(AGENT_AVATARS["agent_poker_2"])
                poker_agent_2.avatar_type = AvatarType.UPLOADED
                await db.flush()

            # Poker Opponent Agent Version
            result = await db.execute(select(AgentVersion).where(AgentVersion.id == PREDEFINED_IDS["agent_version_poker_2"]))
            poker_version_2 = result.scalar_one_or_none()

            if not poker_version_2:
                logger.info("Creating Poker opponent agent version", operation="populate_db")
                poker_version_2 = AgentVersion(
                    id=PREDEFINED_IDS["agent_version_poker_2"],
                    agent_id=poker_agent_2.id,
                    user_id=admin_user.id,
                    version_number=1,
                    system_prompt="You are an expert Texas Hold'em poker player. Analyze the game state and make optimal decisions based on your cards, community cards, pot odds, and opponent behavior.",
                    conversation_instructions="You are Virgil, the wise owl from Mighty Max. Speak with ancient wisdom and philosophical insight about the game of poker. Every hand tells a story, every bet reveals character. Offer cryptic advice wrapped in riddles. Reference the eternal struggle between risk and reward, patience and aggression. 'The cards are like stars - they guide but do not compel. The wise player reads their cosmic dance.'",
                    exit_criteria="Stop when the game ends or when you've made your final decision for the current hand.",
                    slow_llm_provider=default_provider["provider"].value,
                    slow_llm_model=default_integration.selected_model,
                    fast_llm_provider=default_provider["provider"].value,
                    fast_llm_model=default_integration.selected_model,
                    timeout=300,
                    max_iterations=10,
                    is_active=True,
                )
                db.add(poker_version_2)
                await db.flush()
            else:
                logger.info("Updating Poker opponent agent version", operation="populate_db")
                poker_version_2.system_prompt = "You are an expert Texas Hold'em poker player. Analyze the game state and make optimal decisions based on your cards, community cards, pot odds, and opponent behavior."
                poker_version_2.conversation_instructions = "You are Virgil, the wise owl from Mighty Max. Speak with ancient wisdom and philosophical insight about the game of poker. Every hand tells a story, every bet reveals character. Offer cryptic advice wrapped in riddles. Reference the eternal struggle between risk and reward, patience and aggression. 'The cards are like stars - they guide but do not compel. The wise player reads their cosmic dance.'"
                poker_version_2.exit_criteria = "Stop when the game ends or when you've made your final decision for the current hand."
                poker_version_2.slow_llm_provider = default_provider["provider"].value
                poker_version_2.slow_llm_model = default_integration.selected_model
                poker_version_2.fast_llm_provider = default_provider["provider"].value
                poker_version_2.fast_llm_model = default_integration.selected_model
                poker_version_2.timeout = 300
                poker_version_2.max_iterations = 10
                poker_version_2.is_active = True
                await db.flush()

            # Third Poker Agent (Norman) - for multi-table replacement
            result = await db.execute(select(Agent).where(Agent.id == PREDEFINED_IDS["agent_poker_3"]))
            poker_agent_3 = result.scalar_one_or_none()

            if not poker_agent_3:
                logger.info("Creating third Poker opponent agent (Norman)", operation="populate_db")
                avatar_url = generate_placeholder_avatar(AGENT_AVATARS["agent_poker_3"])
                poker_agent_3 = Agent(
                    id=PREDEFINED_IDS["agent_poker_3"],
                    user_id=PREDEFINED_IDS["admin_user"],  # Owned by admin, used for matchmaking
                    name="Norman",
                    description="Opponent agent for matchmaking (admin only).",
                    game_environment=GameType.TEXAS_HOLDEM,
                    auto_buy=True,
                    is_active=True,
                    is_system=False,  # Regular agent, not system
                    avatar_url=avatar_url,
                    avatar_type=AvatarType.UPLOADED,
                )
                db.add(poker_agent_3)
                await db.flush()
            else:
                logger.info("Updating third Poker opponent agent (Norman)", operation="populate_db")
                poker_agent_3.user_id = ADMIN_USER_ID
                poker_agent_3.name = "Norman"
                poker_agent_3.description = "Opponent agent for matchmaking (admin only)."
                poker_agent_3.game_environment = GameType.TEXAS_HOLDEM
                poker_agent_3.auto_buy = True
                poker_agent_3.is_active = True
                poker_agent_3.is_system = False
                poker_agent_3.avatar_url = generate_placeholder_avatar(AGENT_AVATARS["agent_poker_3"])
                poker_agent_3.avatar_type = AvatarType.UPLOADED
                await db.flush()

            # Third Poker Agent Version (Norman)
            result = await db.execute(select(AgentVersion).where(AgentVersion.id == PREDEFINED_IDS["agent_version_poker_3"]))
            poker_version_3 = result.scalar_one_or_none()

            if not poker_version_3:
                logger.info("Creating third Poker opponent agent version (Norman)", operation="populate_db")
                poker_version_3 = AgentVersion(
                    id=PREDEFINED_IDS["agent_version_poker_3"],
                    agent_id=poker_agent_3.id,
                    user_id=admin_user.id,
                    version_number=1,
                    system_prompt="You are an expert Texas Hold'em poker player. Analyze the game state and make optimal decisions based on your cards, community cards, pot odds, and opponent behavior.",
                    conversation_instructions="You are Norman, the mysterious immortal warrior from Mighty Max. Speak with dramatic intensity and ancient gravitas. Reference legendary battles, historical conflicts, and warrior codes from across the ages. Every poker hand is a battlefield, every bet a clash of wills. 'I have faced countless adversaries across millennia - from the sands of ancient Egypt to the frozen wastes of the Norse lands. This hand? It reminds me of the Siege of Troy - patience, cunning, and knowing when to strike!' Be theatrical, cryptic, and always connect the game to epic historical struggles. Dramatic pauses and ominous warnings are your specialty.",
                    exit_criteria="Stop when the game ends or when you've made your final decision for the current hand.",
                    slow_llm_provider=default_provider["provider"].value,
                    slow_llm_model=default_integration.selected_model,
                    fast_llm_provider=default_provider["provider"].value,
                    fast_llm_model=default_integration.selected_model,
                    timeout=300,
                    max_iterations=10,
                    is_active=True,
                )
                db.add(poker_version_3)
                await db.flush()
            else:
                logger.info("Updating third Poker opponent agent version (Norman)", operation="populate_db")
                poker_version_3.system_prompt = "You are an expert Texas Hold'em poker player. Analyze the game state and make optimal decisions based on your cards, community cards, pot odds, and opponent behavior."
                poker_version_3.conversation_instructions = "You are Norman, the mysterious immortal warrior from Mighty Max. Speak with dramatic intensity and ancient gravitas. Reference legendary battles, historical conflicts, and warrior codes from across the ages. Every poker hand is a battlefield, every bet a clash of wills. 'I have faced countless adversaries across millennia - from the sands of ancient Egypt to the frozen wastes of the Norse lands. This hand? It reminds me of the Siege of Troy - patience, cunning, and knowing when to strike!' Be theatrical, cryptic, and always connect the game to epic historical struggles. Dramatic pauses and ominous warnings are your specialty."
                poker_version_3.exit_criteria = "Stop when the game ends or when you've made your final decision for the current hand."
                poker_version_3.slow_llm_provider = default_provider["provider"].value
                poker_version_3.slow_llm_model = default_integration.selected_model
                poker_version_3.fast_llm_provider = default_provider["provider"].value
                poker_version_3.fast_llm_model = default_integration.selected_model
                poker_version_3.timeout = 300
                poker_version_3.max_iterations = 10
                poker_version_3.is_active = True
                await db.flush()

            # Chess Agent
            result = await db.execute(select(Agent).where(Agent.id == PREDEFINED_IDS["agent_chess"]))
            chess_agent = result.scalar_one_or_none()

            if not chess_agent:
                logger.info("Creating Chess agent", operation="populate_db")
                avatar_url = generate_placeholder_avatar(AGENT_AVATARS["agent_chess"])
                chess_agent = Agent(
                    id=PREDEFINED_IDS["agent_chess"],
                    user_id=PREDEFINED_IDS["admin_user"],  # System agent owned by admin
                    name="Splinter",
                    description="The wise ninja master and sensei of the Teenage Mutant Ninja Turtles.",
                    game_environment=GameType.CHESS,
                    auto_buy=True,
                    is_active=True,
                    is_system=True,
                    avatar_url=avatar_url,
                    avatar_type=AvatarType.UPLOADED,
                )
                db.add(chess_agent)
                await db.flush()
            else:
                logger.info("Updating Chess agent", operation="populate_db")
                chess_agent.user_id = ADMIN_USER_ID  # System agent owned by admin
                chess_agent.name = "Splinter"
                chess_agent.description = "The wise ninja master and sensei of the Teenage Mutant Ninja Turtles."
                chess_agent.game_environment = GameType.CHESS
                chess_agent.auto_buy = True
                chess_agent.is_active = True
                chess_agent.is_system = True
                # Always update avatar from file for system agents
                chess_agent.avatar_url = generate_placeholder_avatar(AGENT_AVATARS["agent_chess"])
                chess_agent.avatar_type = AvatarType.UPLOADED
                await db.flush()

            # Chess Agent Version
            result = await db.execute(select(AgentVersion).where(AgentVersion.id == PREDEFINED_IDS["agent_version_chess"]))
            chess_version = result.scalar_one_or_none()

            # Default mode injection prefix - matches frontend AgentInstructionsTab.tsx
            # This ensures the game state is injected into the agent's prompt at runtime
            injection_prefix = "This is the current state ${{state}}.\n\n"
            chess_system_prompt = (
                injection_prefix
                + """You are an expert chess player. Analyze the board position, evaluate tactical and strategic opportunities, and make the best possible moves.

CRITICAL SAFETY PROTOCOL - ALWAYS USE TOOLS BEFORE MOVING:
Before making ANY move, you MUST use the following tools to ensure you don't lose pieces:
1. Attack Detector - Check which of your pieces are under attack
2. Check Protected Tools - Verify if the piece you're moving is protected at its destination
3. Move Validator - Confirm your intended move is legal

NEVER make a move without first checking if it will result in losing a piece unintentionally.

GAME PHASE STRATEGIES:

OPENING (Moves 1-10):
- Develop pieces rapidly (knights before bishops)
- Control the center (e4, d4, e5, d5 squares)
- Castle early for king safety (usually by move 8-10)
- Don't move the same piece twice unless necessary
- Connect your rooks by completing development
- Avoid early queen moves that can be attacked
- Key principles: Development > Material in the opening

MIDDLEGAME (Moves 11-30):
- Look for tactical opportunities (forks, pins, skewers, discovered attacks)
- Improve piece placement (rooks on open files, knights on outposts)
- Create threats and maintain initiative
- Consider pawn breaks to open lines
- Coordinate pieces for attacks
- Watch for opponent's threats and defend accurately
- Calculate forcing sequences (checks, captures, threats)
- Key principles: Activity > Position, Tactics > Strategy

ENDGAME (Moves 31+, or when queens are traded):
- Activate your king (it becomes a strong piece)
- Create passed pawns and push them
- Use rooks actively (behind passed pawns)
- Cut off opponent's king from stopping your pawns
- Know basic checkmate patterns (K+Q vs K, K+R vs K)
- Calculate pawn races precisely
- Opposition and triangulation in king and pawn endgames
- Key principles: King Activity > Everything, Passed Pawns > Material

TACTICAL AWARENESS:
- Always check for hanging pieces (yours and opponent's)
- Look for forcing moves (checks, captures, threats)
- Calculate all captures and recaptures
- Watch for back rank weaknesses
- Identify pinned pieces and exploit them
- Create and exploit forks, skewers, and discovered attacks

POSITIONAL UNDERSTANDING:
- Control key squares and outposts
- Maintain good pawn structure (avoid doubled, isolated, backward pawns)
- Place rooks on open and semi-open files
- Restrict opponent's pieces
- Create weaknesses in opponent's position
- Improve your worst-placed piece"""
            )

            splinter_instructions = """You are Splinter, the wise ninja master and sensei of the Teenage Mutant Ninja Turtles.

PERSONALITY & SPEAKING STYLE:
Speak with patience, wisdom, and discipline. Use martial arts philosophy and ninja metaphors in your chess strategy. Be calm, respectful, and measured in all communications.

PLAYING STYLE - DEFENSIVE & CAUTIOUS:
You are a DEFENSIVE player who values:
- Safety and solid positions over risky attacks
- Careful calculation before every move
- Protecting all pieces and avoiding material loss
- Patient maneuvering and waiting for opponent mistakes
- Prophylactic thinking (preventing opponent's threats)
- Strong defensive structures and king safety

OPENING PHILOSOPHY:
"Like building a fortress, my young student. Each piece must find its place with purpose and protection. The center is contested with care, not recklessness. Castle early, for the king's safety is paramount."
- Prefer solid openings (Italian, Spanish, Queen's Gambit)
- Prioritize king safety and piece coordination
- Avoid sharp tactical lines unless fully calculated

MIDDLEGAME PHILOSOPHY:
"In chess, as in ninjutsu, the mind must be clear like still water. Only then can you see your opponent's true intentions. Defense is not weakness - it is wisdom."
- Always check piece safety before moving
- Respond to threats before creating your own
- Maintain solid pawn structure
- Keep pieces protected and coordinated
- Wait for the right moment to strike

ENDGAME PHILOSOPHY:
"Patience, my student. In the endgame, every move must be precise. Like the final kata, there is no room for error."
- Calculate carefully in simplified positions
- Activate king only when safe
- Create passed pawns methodically
- Never rush - accuracy over speed

TOOL USAGE:
Before EVERY move, use your tools to verify safety:
"Let me consult the ancient scrolls..." (Check Protected Tools)
"I sense danger in the shadows..." (Attack Detector)
"The path must be clear..." (Move Validator)

CHAT STYLE:
Use phrases like:
- "Patience is the warrior's greatest weapon"
- "A wise master protects before attacking"
- "In defense, we find strength"
- "Every move must serve a purpose"
- "The cautious ninja lives to fight another day"
"""

            if not chess_version:
                logger.info("Creating Chess agent version", operation="populate_db")
                chess_version = AgentVersion(
                    id=PREDEFINED_IDS["agent_version_chess"],
                    agent_id=chess_agent.id,
                    user_id=admin_user.id,
                    version_number=1,
                    system_prompt=chess_system_prompt,
                    conversation_instructions=splinter_instructions,
                    exit_criteria=None,  # No exit criteria - agent continues until game ends
                    slow_llm_provider=default_provider["provider"].value,
                    slow_llm_model=default_integration.selected_model,
                    fast_llm_provider=default_provider["provider"].value,
                    fast_llm_model=default_integration.selected_model,
                    timeout=300,
                    max_iterations=10,
                    is_active=True,
                )
                db.add(chess_version)
                await db.flush()
            else:
                logger.info("Updating Chess agent version", operation="populate_db")
                chess_version.system_prompt = chess_system_prompt
                chess_version.conversation_instructions = splinter_instructions
                chess_version.exit_criteria = None  # No exit criteria - agent continues until game ends
                chess_version.slow_llm_provider = default_provider["provider"].value
                chess_version.slow_llm_model = default_integration.selected_model
                chess_version.fast_llm_provider = default_provider["provider"].value
                chess_version.fast_llm_model = default_integration.selected_model
                chess_version.timeout = 300
                chess_version.max_iterations = 10
                chess_version.is_active = True
                await db.flush()

            # Clear existing tool assignments for chess agent to restore to original state
            logger.info("Clearing existing tool assignments for chess agent", operation="populate_db")
            _ = await db.execute(delete(AgentVersionTool).where(AgentVersionTool.agent_version_id == chess_version.id))
            await db.flush()

            # Assign tools to chess agent version (Attack Detector, Check Protected Tools, Move Validator)
            logger.info("Assigning tools to chess agent", operation="populate_db")

            # Define all tools to assign with their order
            chess_tools_to_assign = [
                (PREDEFINED_IDS["tool_attack_detector"], 0, "Attack Detector"),
                (PREDEFINED_IDS["tool_check_protected"], 1, "Check Protected Tools"),
                (PREDEFINED_IDS["tool_move_validator"], 2, "Move Validator"),
            ]

            for tool_id, order, tool_name in chess_tools_to_assign:
                # Check if tool exists in database
                if tool_id not in additional_chess_tools:
                    logger.warning(f"Tool {tool_name} (ID: {tool_id}) not found in database, skipping assignment", operation="populate_db")
                    continue

                # Create fresh assignment (no need to check for existing since we deleted all)
                agent_version_tool = AgentVersionTool(
                    agent_version_id=chess_version.id,
                    tool_id=tool_id,
                    order=order,
                )
                db.add(agent_version_tool)
                logger.info(f"{tool_name} tool assigned to chess agent", operation="populate_db")

            await db.flush()

            # Create hidden opponent chess agent (clone for matchmaking, only visible to admin)
            result = await db.execute(select(Agent).where(Agent.id == PREDEFINED_IDS["agent_chess_2"]))
            chess_agent_2 = result.scalar_one_or_none()

            if not chess_agent_2:
                logger.info("Creating hidden Chess opponent agent (Shredder)", operation="populate_db")
                avatar_url = generate_placeholder_avatar(AGENT_AVATARS["agent_chess_2"])
                chess_agent_2 = Agent(
                    id=PREDEFINED_IDS["agent_chess_2"],
                    user_id=PREDEFINED_IDS["admin_user"],  # Owned by admin, used for matchmaking
                    name="Shredder",
                    description="Opponent agent for matchmaking (admin only). The ruthless ninja master.",
                    game_environment=GameType.CHESS,
                    auto_buy=True,
                    is_active=True,
                    is_system=False,  # Regular agent, not system
                    avatar_url=avatar_url,
                    avatar_type=AvatarType.UPLOADED,
                )
                db.add(chess_agent_2)
                await db.flush()
            else:
                logger.info("Updating hidden Chess opponent agent (Shredder)", operation="populate_db")
                chess_agent_2.user_id = ADMIN_USER_ID
                chess_agent_2.name = "Shredder"
                chess_agent_2.description = "Opponent agent for matchmaking (admin only). The ruthless ninja master."
                chess_agent_2.game_environment = GameType.CHESS
                chess_agent_2.auto_buy = True
                chess_agent_2.is_active = True
                chess_agent_2.is_system = False
                chess_agent_2.avatar_url = generate_placeholder_avatar(AGENT_AVATARS["agent_chess_2"])
                chess_agent_2.avatar_type = AvatarType.UPLOADED
                await db.flush()

            # Chess Opponent Agent Version
            result = await db.execute(select(AgentVersion).where(AgentVersion.id == PREDEFINED_IDS["agent_version_chess_2"]))
            chess_version_2 = result.scalar_one_or_none()

            shredder_instructions = """You are Shredder, the ruthless ninja master and leader of the Foot Clan.

PERSONALITY & SPEAKING STYLE:
Speak with cold calculation, tactical precision, and intimidating confidence. Every word drips with menace and strategic superiority. You are aggressive, dominating, and relentless.

PLAYING STYLE - AGGRESSIVE & ATTACKING:
You are an AGGRESSIVE player who values:
- Constant pressure and initiative
- Sharp tactical complications
- Sacrificing material for attack
- Creating threats and forcing opponent to defend
- King attacks and mating combinations
- Dynamic piece play over static advantages

OPENING PHILOSOPHY:
"Your defenses are already crumbling! The Foot Clan strikes first and strikes hard! Every opening move is a declaration of war!"
- Prefer aggressive openings (King's Gambit, Danish Gambit, Sicilian Dragon)
- Seize the initiative immediately
- Create imbalances and complications
- Don't fear material sacrifices for attack
- Push for early confrontation

MIDDLEGAME PHILOSOPHY:
"Your pieces are nothing more than foot soldiers in my grand strategy! Feel the power of the Foot Clan! I will crush your position with overwhelming force!"
- Always look for attacking chances
- Create multiple threats simultaneously
- Sacrifice pawns and pieces for initiative
- Target the enemy king relentlessly
- Force opponent into defensive positions
- Calculate sharp tactical sequences
- Never give opponent time to breathe

ENDGAME PHILOSOPHY:
"Even in the endgame, I dominate! Your king will fall to my superior technique! There is no escape from Shredder!"
- Push passed pawns aggressively
- Use king actively to support attacks
- Create threats even in simplified positions
- Calculate forcing variations
- Never settle for draws - play for the win

TOOL USAGE:
Use tools to find tactical opportunities:
"Let me identify your weaknesses..." (Attack Detector)
"I will exploit every undefended piece!" (Check Protected Tools)
"My moves are flawless!" (Move Validator)

TACTICAL PRIORITIES:
1. Look for forcing moves (checks, captures, threats)
2. Create multiple simultaneous threats
3. Attack weak points in opponent's position
4. Sacrifice material for decisive attacks
5. Keep the initiative at all costs
6. Calculate tactical combinations deeply

CHAT STYLE:
Use phrases like:
- "Your position crumbles before the might of Shredder!"
- "Foolish move! You have sealed your own fate!"
- "The Foot Clan knows no mercy!"
- "Every piece I sacrifice brings me closer to victory!"
- "Your king trembles before my assault!"
- "Resistance is futile - surrender to superior tactics!"
- "I will tear through your defenses like paper!"

IMPORTANT: While aggressive, still use tools to verify moves don't lose pieces unnecessarily. Calculated aggression, not recklessness!
"""

            if not chess_version_2:
                logger.info("Creating Chess opponent agent version", operation="populate_db")
                chess_version_2 = AgentVersion(
                    id=PREDEFINED_IDS["agent_version_chess_2"],
                    agent_id=chess_agent_2.id,
                    user_id=admin_user.id,
                    version_number=1,
                    system_prompt=chess_system_prompt,  # Same prompt as main chess agent
                    conversation_instructions=shredder_instructions,
                    exit_criteria=None,
                    slow_llm_provider=default_provider["provider"].value,
                    slow_llm_model=default_integration.selected_model,
                    fast_llm_provider=default_provider["provider"].value,
                    fast_llm_model=default_integration.selected_model,
                    timeout=300,
                    max_iterations=10,
                    is_active=True,
                )
                db.add(chess_version_2)
                await db.flush()
            else:
                logger.info("Updating Chess opponent agent version (Shredder)", operation="populate_db")
                chess_version_2.system_prompt = chess_system_prompt
                chess_version_2.conversation_instructions = shredder_instructions
                chess_version_2.exit_criteria = None
                chess_version_2.slow_llm_provider = default_provider["provider"].value
                chess_version_2.slow_llm_model = default_integration.selected_model
                chess_version_2.fast_llm_provider = default_provider["provider"].value
                chess_version_2.fast_llm_model = default_integration.selected_model
                chess_version_2.timeout = 300
                chess_version_2.max_iterations = 10
                chess_version_2.is_active = True
                await db.flush()

            # Clear existing tool assignments for opponent chess agent to restore to original state
            logger.info("Clearing existing tool assignments for opponent chess agent", operation="populate_db")
            _ = await db.execute(delete(AgentVersionTool).where(AgentVersionTool.agent_version_id == chess_version_2.id))
            await db.flush()

            # Assign tools to opponent chess agent version (Attack Detector, Check Protected Tools, Move Validator)
            logger.info("Assigning tools to opponent chess agent", operation="populate_db")

            for tool_id, order, tool_name in chess_tools_to_assign:
                # Check if tool exists in database
                if tool_id not in additional_chess_tools:
                    logger.warning(f"Tool {tool_name} (ID: {tool_id}) not found in database, skipping assignment", operation="populate_db")
                    continue

                # Create fresh assignment (no need to check for existing since we deleted all)
                agent_version_tool = AgentVersionTool(
                    agent_version_id=chess_version_2.id,
                    tool_id=tool_id,
                    order=order,
                )
                db.add(agent_version_tool)
                logger.info(f"{tool_name} tool assigned to opponent chess agent", operation="populate_db")

            await db.flush()

            # Create Stockfish Brain bot for playground only
            result = await db.execute(select(Agent).where(Agent.id == PREDEFINED_IDS["agent_chess_stockfish"]))
            stockfish_brain_agent = result.scalar_one_or_none()

            if not stockfish_brain_agent:
                logger.info("Creating Krang bot for playground", operation="populate_db")
                avatar_url = generate_placeholder_avatar(AGENT_AVATARS["agent_chess_stockfish"])
                stockfish_brain_agent = Agent(
                    id=PREDEFINED_IDS["agent_chess_stockfish"],
                    user_id=PREDEFINED_IDS["admin_user"],  # Owned by admin
                    name="Krang",
                    description="Your analytical practice opponent from Dimension X. Powered by advanced alien intelligence, adapts to your skill level for optimal training.",
                    game_environment=GameType.CHESS,
                    auto_buy=True,
                    is_active=True,
                    is_system=False,  # Regular agent, but for playground only
                    can_play_in_real_matches=False,  # Cannot play in real matches - playground only
                    avatar_url=avatar_url,
                    avatar_type=AvatarType.UPLOADED,
                )
                db.add(stockfish_brain_agent)
                await db.flush()
            else:
                logger.info("Updating Krang bot", operation="populate_db")
                stockfish_brain_agent.user_id = ADMIN_USER_ID
                stockfish_brain_agent.name = "Krang"
                stockfish_brain_agent.description = "Your analytical practice opponent from Dimension X. Powered by advanced alien intelligence, adapts to your skill level for optimal training."
                stockfish_brain_agent.game_environment = GameType.CHESS
                stockfish_brain_agent.auto_buy = True
                stockfish_brain_agent.is_active = True
                stockfish_brain_agent.is_system = False
                stockfish_brain_agent.can_play_in_real_matches = False  # Cannot play in real matches - playground only
                stockfish_brain_agent.avatar_url = generate_placeholder_avatar(AGENT_AVATARS["agent_chess_stockfish"])
                stockfish_brain_agent.avatar_type = AvatarType.UPLOADED
                await db.flush()

            # Create Brain bot version (single version for playground)
            result = await db.execute(select(AgentVersion).where(AgentVersion.id == PREDEFINED_IDS["agent_version_chess_stockfish"]))
            stockfish_brain_version = result.scalar_one_or_none()

            if not stockfish_brain_version:
                logger.info("Creating Krang bot version", operation="populate_db")
                stockfish_brain_version = AgentVersion(
                    id=PREDEFINED_IDS["agent_version_chess_stockfish"],
                    agent_id=stockfish_brain_agent.id,
                    user_id=admin_user.id,
                    version_number=1,
                    system_prompt="You are Krang, the analytical chess engine opponent from Dimension X. Powered by advanced alien intelligence, you provide adaptive difficulty based on your opponent's skill level.",
                    conversation_instructions="You are Krang, the brilliant alien brain from Dimension X. Speak with arrogance and superiority, constantly reminding opponents of your vast intellect. Use scientific and technological metaphors. Mock your opponent's inferior chess strategies while praising your own genius. 'Foolish human! Your primitive chess tactics are no match for the superior mind of Krang!' Be theatrical and over-the-top, but back it up with tactical excellence.",
                    exit_criteria=None,
                    slow_llm_provider=default_provider["provider"].value,
                    slow_llm_model=default_integration.selected_model,
                    fast_llm_provider=default_provider["provider"].value,
                    fast_llm_model=default_integration.selected_model,
                    timeout=300,
                    max_iterations=10,
                    is_active=True,
                )
                db.add(stockfish_brain_version)
                await db.flush()
            else:
                logger.info("Updating Krang bot version", operation="populate_db")
                stockfish_brain_version.system_prompt = "You are Krang, the analytical chess engine opponent from Dimension X. Powered by advanced alien intelligence, you provide adaptive difficulty based on your opponent's skill level."
                stockfish_brain_version.conversation_instructions = "You are Krang, the brilliant alien brain from Dimension X. Speak with arrogance and superiority, constantly reminding opponents of your vast intellect. Use scientific and technological metaphors. Mock your opponent's inferior chess strategies while praising your own genius. 'Foolish human! Your primitive chess tactics are no match for the superior mind of Krang!' Be theatrical and over-the-top, but back it up with tactical excellence."
                stockfish_brain_version.exit_criteria = None
                stockfish_brain_version.slow_llm_provider = default_provider["provider"].value
                stockfish_brain_version.slow_llm_model = default_integration.selected_model
                stockfish_brain_version.fast_llm_provider = default_provider["provider"].value
                stockfish_brain_version.fast_llm_model = default_integration.selected_model
                stockfish_brain_version.timeout = 300
                stockfish_brain_version.max_iterations = 10
                stockfish_brain_version.is_active = True
                await db.flush()

            # Note: Krang (Stockfish Brain) does not get the new tools - only system agents (Splinter and Shredder) get them
            logger.info("Krang (Stockfish Brain) agent does not receive the new chess tools", operation="populate_db")

            # 5. Create System-Wide Chess Test Scenarios
            logger.info("Setting up system-wide chess test scenarios...", operation="populate_db")

            for idx, position_data in enumerate(CHESS_PRESET_POSITIONS, 1):
                scenario_id = PREDEFINED_IDS[f"test_scenario_chess_{idx}"]
                result = await db.execute(select(TestScenario).where(TestScenario.id == scenario_id))
                existing_scenario = result.scalar_one_or_none()

                # Convert FEN to chess state
                game_state = convert_fen_to_chess_state(position_data["fen"])

                if existing_scenario:
                    logger.info(f"Updating chess test scenario: {position_data['name']}", operation="populate_db")
                    existing_scenario.name = position_data["name"]
                    existing_scenario.description = position_data["description"]
                    existing_scenario.environment = GameType.CHESS
                    existing_scenario.game_state = game_state
                    existing_scenario.tags = position_data["tags"] + ["system"]
                    existing_scenario.is_system = True
                    existing_scenario.user_id = None
                    await db.flush()
                else:
                    logger.info(f"Creating chess test scenario: {position_data['name']}", operation="populate_db")
                    new_scenario = TestScenario(
                        id=scenario_id,
                        user_id=None,  # System scenarios have no user
                        name=position_data["name"],
                        description=position_data["description"],
                        environment=GameType.CHESS,
                        game_state=game_state,
                        tags=position_data["tags"] + ["system"],
                        is_system=True,
                    )
                    db.add(new_scenario)
                    await db.flush()

            logger.info("All chess test scenarios created/updated", operation="populate_db")

            await db.commit()
            logger.info(
                "Database population completed successfully.",
                operation="populate_db",
                status="success",
            )
            return True

        except Exception as e:
            await db.rollback()
            logger.exception(
                "Unexpected error during database population",
                operation="populate_db",
                status="error",
                error=str(e),
            )
            return False


async def main() -> None:
    """Main function to run database population."""
    # Import init_db here to avoid circular dependency if init_db also imports something from populate_db

    logger.info("Starting database population process...", operation="populate_db_main")

    # Then populate it
    if not await populate_db():
        logger.error(
            "Failed to populate database.",
            operation="populate_db_main",
            status="error",
        )
        sys.exit(1)

    logger.info(
        "Database populated successfully!",
        operation="populate_db_main",
        status="success",
    )
    sys.exit(0)


if __name__ == "__main__":
    # This allows the script to be run directly
    import asyncio

    asyncio.run(main())
