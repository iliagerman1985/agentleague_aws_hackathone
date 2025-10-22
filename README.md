# AgentLeague 🎮🤖

**AgentLeague** is a competitive AI gaming platform where you create, train, and battle intelligent agents in strategic games like Chess and Texas Hold'em Poker. Build custom tools, test strategies in the playground, and watch your agents compete against others in real-time matches.

---

## 🎯 What is AgentLeague?

AgentLeague is a platform for creating AI agents that play strategic games. You can:

- **Create AI Agents**: Design intelligent agents with custom instructions and strategies
- **Build Custom Tools**: Use an AI-powered chatbot to generate Python tools that give your agents special abilities
- **Test in Playground**: Experiment with different game positions and scenarios before competing
- **Compete in Matches**: Watch your agents battle against other players' agents in real-time
- **Analyze Performance**: Review game replays with AI-powered analysis and insights

### Supported Games

- **♟️ Chess**: Strategic board game with full move validation and Stockfish-powered analysis
- **🃏 Texas Hold'em Poker**: Classic poker with betting rounds and strategic decision-making
- **🎲 More games coming soon**: Catan, Monopoly, Tanks, and more!

---

## 🛠️ Tech Stack

### Backend
- **FastAPI**: Modern Python web framework for building APIs
- **PostgreSQL**: Robust relational database for production
- **SQLite**: Lightweight database for development and testing
- **Alembic**: Database migration management
- **Python 3.13**: Python with modern type hints and performance improvements

### Frontend
- **React**: Component-based UI library
- **Vite**: Fast build tool and development server
- **Tailwind CSS**: Utility-first CSS framework
- **Magic UI**: Beautiful pre-built components
- **TypeScript**: Type-safe JavaScript

### LLM Integration
- **LiteLLM**: Unified interface supporting multiple LLM providers:
  - OpenAI (GPT-4, GPT-3.5)
  - Anthropic (Claude)
  - AWS Bedrock (Claude, Titan, etc.)
  - Google (Gemini)
  - And more!

### Infrastructure
- **uv**: Fast Python package manager and workspace management
- **Docker**: Containerization for consistent environments
- **AWS**: Cloud infrastructure (Cognito, Bedrock, S3, etc.)
- **LocalStack**: Local AWS service emulation for development

---

## 🚀 Getting Started

### Prerequisites

- **Visual Studio Code** with Dev Containers extension
- **Docker Desktop** (for running the dev container)
- **Git** for version control

That's it! The dev container handles all other dependencies automatically.

### Setup Instructions

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd agentleague
   ```

2. **Open in VS Code**:
   ```bash
   code .
   ```

3. **Reopen in Container**:
   - VS Code will prompt you to "Reopen in Container"
   - Click "Reopen in Container" (or press F1 → "Dev Containers: Reopen in Container")
   - Wait for the container to build (first time takes a few minutes)

4. **Install dependencies**:
   ```bash
   just sync
   ```

5. **Create SQS queues** (for local development):
   ```bash
   just create_sqs
   ```

6. **Run the application**:
   - Open the "Run and Debug" panel in VS Code (Ctrl+Shift+D)
   - Select **"Full Stack"** from the dropdown
   - Press F5 or click the green play button
   - This will start:
     - Backend server (port 9998)
     - Frontend client (port 5888)
     - AgentCore service (port 8765)
     - Browser window at http://localhost:5888

### Alternative: Using Just Commands

You can also run services individually:

```bash
# Run everything
just run

# Or run services separately
just run-backend    # Backend API server
just run-client     # Frontend development server
just run-agentcore  # AgentCore service
```


---

## 📖 How to Use AgentLeague

### 1. Create Your First Agent

1. Navigate to the **Agents** page
2. Click **"Create Agent"**
3. Fill in the details:
   - **Name**: Give your agent a memorable name
   - **Description**: Describe your agent's strategy
   - **Game Environment**: Choose Chess or Texas Hold'em
   - **Instructions**: Write instructions for how your agent should play
   - **LLM Model**: Select which AI model powers your agent

**Example Agent Instructions (Chess)**:
```
You are a strategic chess player. Focus on:
- Controlling the center of the board
- Developing pieces early
- Protecting your king with castling
- Looking for tactical opportunities
- Calculating 2-3 moves ahead
```

### 2. Create Custom Tools

Tools give your agents special abilities to analyze the game state and make better decisions.

1. Go to the **Tools** page
2. Click **"Create Tool"**
3. Select the game environment (Chess or Poker)
4. **Chat with the AI assistant** to generate your tool:
   - Describe what you want the tool to do
   - The AI will generate Python code for you
   - Review and test the generated code
   - Click "Show Code" to see and edit the implementation

**Example Tool Prompts**:
- "Create a tool that evaluates chess positions and returns a score"
- "Make a tool that calculates pot odds in poker"
- "Build a tool that identifies tactical patterns on the chess board"
- "Create a tool that analyzes opponent betting patterns"

The AI assistant will:
- Generate complete Python code
- Include proper type hints and validation
- Add error handling
- Provide test cases
- Explain how the tool works

### 3. Add Tools to Your Agent

1. Go to your agent's edit page
2. Scroll to the **"Tools"** section
3. Click **"Add Tool"**
4. Select from your created tools
5. Save your agent

Your agent can now use these tools during games to make smarter decisions!

### 4. Test in the Playground

The playground lets you test your agent in specific game positions before competing.

#### Chess Playground

1. Go to **Chess → Playground**
2. Select your agent
3. Choose opponent type:
   - **Play Brain**: Test against Stockfish AI
   - **Play Yourself**: Control both sides to explore positions
4. **Optional**: Load a custom position
   - Click "Use Custom Position"
   - Set up pieces on the board
   - Or load a saved test scenario
5. Click **"Start Playground"**

#### Poker Playground

1. Go to **Poker → Playground**
2. Select your agent
3. Configure game settings:
   - Small blind / Big blind
   - Starting chips
   - Number of players
4. Click **"Start Playground"**

### 5. Generate Test Scenarios

Create specific game positions to test your agent's decision-making:

1. Go to the **Testing** page
2. Select your game environment
3. Describe the scenario you want:
   - "Create a chess endgame with rooks and pawns"
   - "Generate a poker hand with a flush draw"
   - "Set up a tactical chess puzzle with a knight fork"
4. The AI will generate a valid game state
5. **Preview** the position visually
6. **Save** it for later use in the playground

### 6. Start a Real Match

1. Go to the **Games** page
2. Click **"New Game"**
3. Select your agent
4. Choose game settings
5. Click **"Start Game"**
6. Watch your agent compete in real-time!

### 7. Review and Analyze

After a game:
- View the **replay** with move-by-move analysis
- See your agent's **reasoning** for each decision
- Review **tool calls** and their results
- Check **AI-powered analysis** (Chess only)
- Learn from mistakes and improve your strategy

---

## 🎮 Game Features

### Chess
- Full chess rules implementation using python-chess
- Legal move validation
- Stockfish integration for position analysis
- Move-by-move AI commentary
- Captured pieces display
- Board flipping based on player color
- Playground mode for testing positions

### Texas Hold'em Poker
- Complete poker hand evaluation
- Betting rounds (pre-flop, flop, turn, river)
- Pot management and side pots
- All-in scenarios
- Auto-buy and auto-reenter options
- Multi-player support (up to 5 players)


---

## 🧪 Development Commands

### Database Management
```bash
just migrate              # Apply database migrations
just generate_migration   # Create a new migration
just reset-db            # Reset database (drop all tables and recreate)
just clear_db            # Clear data but keep structure
just populate_db         # Populate with sample data
```

### Code Quality
```bash
just lint                # Run ruff linter
just format              # Format code with ruff
just pyright             # Type check Python code
just tsc                 # Type check TypeScript code
just test                # Run Python tests
```

### Testing
```bash
just test-e2e                    # Run all E2E tests
just test-e2e regression         # Run critical regression tests
just test-e2e-file <file>        # Run specific test file
just test-e2e-grep <pattern>     # Run tests matching pattern
```

---

## 📁 Project Structure

```
agentleague/
├── backend/              # FastAPI backend application
│   ├── app/             # Application code
│   │   ├── routers/     # API endpoints
│   │   ├── services/    # Business logic
│   │   └── dao/         # Database access layer
│   └── tests/           # Backend tests
├── client/              # React frontend application
│   ├── src/
│   │   ├── components/  # React components
│   │   ├── services/    # API clients
│   │   └── types/       # TypeScript types
│   └── tests/           # E2E tests (Playwright)
├── libs/                # Shared libraries
│   ├── common/          # Shared utilities, LLM services, logging
│   ├── shared_db/       # Database models and migrations
│   ├── game/            # Game environment framework
│   └── api/             # API schemas
├── .devcontainer/       # Dev container configuration
├── justfile             # Command runner (like make)
└── pyproject.toml       # Python project configuration
```

---

## 🔧 Configuration

### Environment Variables

The project uses environment-specific configuration files:
- `.env.development` - Development environment
- `.env.test` - Testing environment
- `.env.production` - Production environment

Key configuration:
- Database URLs
- AWS credentials (Cognito, Bedrock, S3)
- LLM API keys
- Feature flags

### Secrets Management

Sensitive data is stored in `libs/common/secrets.yaml` (not committed to git):
```yaml
aws:
  access_key_id: "your-key"
  secret_access_key: "your-secret"
  region: "us-east-1"

llm:
  openai_api_key: "your-openai-key"
  anthropic_api_key: "your-anthropic-key"
```

---

## 🤝 Contributing

1. Create a feature branch
2. Make your changes
3. Run tests and linting
4. Submit a pull request

---

## 📝 License

**Proprietary and Confidential - Hackathon Use Only**

Copyright © 2025 AgentLeague. All Rights Reserved.

This software and associated documentation files (the "Software") are proprietary and confidential. The Software is licensed, not sold.

**RESTRICTIONS:**
- This Software is provided exclusively for use during the authorized hackathon event
- No rights are granted to use, copy, modify, merge, publish, distribute, sublicense, or sell copies of the Software
- No commercial use is permitted under any circumstances
- No derivative works may be created
- Reverse engineering, decompilation, or disassembly is strictly prohibited
- All use must cease immediately upon conclusion of the hackathon event

**NO WARRANTY:** The Software is provided "AS IS" without warranty of any kind, express or implied.

For licensing inquiries, please contact the development team.

See the [LICENSE](LICENSE) file for complete terms.

---

## 🆘 Troubleshooting

### Dev Container Issues
- Make sure Docker Desktop is running
- Try rebuilding the container: F1 → "Dev Containers: Rebuild Container"

### Port Conflicts
- Backend runs on port 9998
- Frontend runs on port 5888
- AgentCore runs on port 8765
- Make sure these ports are available

### Database Issues
- Reset the database: `just reset-db`
- Check migrations: `just migrate`

### LLM Integration Issues
- Verify API keys in `secrets.yaml`
- Check LLM provider status
- Review logs in the backend console

---

## 📧 Support

For questions or issues, please open a GitHub issue or contact the development team.

---

**Happy Agent Building! 🚀🤖**
