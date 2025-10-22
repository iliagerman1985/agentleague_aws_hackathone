#!/bin/bash

# DevContainer Post-Create Setup Script
# This script sets up the development environment after the container is created

set -e  # Exit on any error

echo "🚀 Starting DevContainer setup..."

# Add host.docker.internal to /etc/hosts for proper networking
echo "📝 Configuring host networking..."
echo 'host.docker.internal host-gateway' >> /etc/hosts

# Verify Docker installation
echo "🐳 Verifying Docker installation..."
docker --version

# Fix GPG key issues and update package lists
echo "📦 Fixing GPG keys and updating package lists..."

# Fix GPG keys for repositories
echo "🔑 Fixing GPG keys for package repositories..."

# Remove all problematic repository sources temporarily
sudo rm -f /etc/apt/sources.list.d/microsoft-prod.list
sudo rm -f /etc/apt/sources.list.d/microsoft.list
sudo rm -f /etc/apt/sources.list.d/yarn.list

# Fix GPG keyring issues
echo "🔧 Fixing GPG keyring..."
sudo apt-get clean
sudo rm -rf /var/lib/apt/lists/*
sudo mkdir -p /var/lib/apt/lists/partial

# Update with minimal repositories first (skip problematic ones)
echo "📦 Updating with basic repositories..."
sudo apt-get update --allow-insecure-repositories -o Acquire::AllowInsecureRepositories=true || true

# Install essential packages without GPG verification for now
echo "🔧 Installing essential packages..."
sudo apt-get install -y --allow-unauthenticated curl wget gnupg2 software-properties-common apt-transport-https ca-certificates git-lfs || true

# Install Just (command runner)
echo "⚡ Installing Just command runner..."
if [ ! -f /usr/local/bin/just ]; then
    curl --proto '=https' --tlsv1.2 -sSf https://just.systems/install.sh | bash -s -- --to /usr/local/bin
else
    echo "✓ Just is already installed"
fi

# Install system dependencies (allow unauthenticated for DevContainer)
echo "🔧 Installing system dependencies..."
sudo apt-get install -y --allow-unauthenticated libpq-dev python3-dev gcc iputils-ping build-essential stockfish || true

# Create symlink for Stockfish (installed to /usr/games/stockfish)
echo "♟️  Setting up Stockfish..."
if [ -f /usr/games/stockfish ]; then
    sudo ln -sf /usr/games/stockfish /usr/local/bin/stockfish
    echo "✓ Stockfish symlink created at /usr/local/bin/stockfish"
else
    echo "⚠️  Stockfish not found at /usr/games/stockfish"
fi

# Create symlink for Stockfish (installed in /usr/games by default)
echo "♟️  Setting up Stockfish..."
if [ -f /usr/games/stockfish ]; then
    sudo ln -sf /usr/games/stockfish /usr/local/bin/stockfish
    echo "✓ Stockfish symlink created at /usr/local/bin/stockfish"
else
    echo "⚠️  Stockfish not found at /usr/games/stockfish"
fi

# echo "Installing OpenCode"
# npm i -g opencode-ai@latest        # or bun/pnpm/yarn
# if [ ! -f "$HOME/.opencode/bin/opencode" ]; then
#     curl -fsSL https://opencode.ai/install | bash
#     # Ensure the binary has execute permissions
#     chmod +x "$HOME/.opencode/bin/opencode" 2>/dev/null || true
#     # Add to PATH if not already there
#     if [[ ":$PATH:" != *":$HOME/.opencode/bin:"* ]]; then
#         export PATH="$HOME/.opencode/bin:$PATH"
#         echo 'export PATH="$HOME/.opencode/bin:$PATH"' >> ~/.bashrc
#     fi
# else
#     echo "✓ OpenCode is already installed"
#     # Still ensure proper permissions and PATH
#     chmod +x "$HOME/.opencode/bin/opencode" 2>/dev/null || true
#     if [[ ":$PATH:" != *":$HOME/.opencode/bin:"* ]]; then
#         export PATH="$HOME/.opencode/bin:$PATH"
#     fi
# fi

#install claude code cli
npm install -g @anthropic-ai/claude-code
# Install uv first
echo "📦 Installing uv package manager..."
if [ ! -f "$HOME/.local/bin/uv" ]; then
    curl -LsSf https://astral.sh/uv/install.sh | sh
else
    echo "✓ uv is already installed"
fi
export PATH="$HOME/.local/bin:$PATH"

# Install Python dependencies using uv
echo "🐍 Installing Python dependencies with uv..."

# Install all workspace dependencies
echo "📦 Installing workspace dependencies..."
uv sync

# Verify installation
echo "✅ Verifying installation..."
uv run --package backend python -c "import fastapi; print('✓ FastAPI installed')"
uv run --package backend python -c "import uvicorn; print('✓ Uvicorn installed')"
uv run --package backend python -c "from common.core.config_service import ConfigService; print('✓ Common library installed')"
uv run --package backend python -c "from shared_db.db import Base; print('✓ Shared DB library installed')"

echo "🎉 All Python dependencies installed successfully!"

# Install frontend dependencies if client directory exists
if [ -d 'client' ]; then
    echo "🎨 Installing frontend dependencies..."
    cd client && npm install && npx playwright install-deps && npx playwright install && cd ..
else
    echo "⚠️  No client directory found, skipping npm install..."
fi

# Configure Git
echo "🔧 Configuring Git..."
git config --global user.email 'iliagerman@gmail.com'
git config --global user.name 'Ilia German'

# Install LocalStack CLI
echo "☁️  Installing LocalStack CLI..."
if [ ! -f /usr/local/bin/localstack ]; then
    curl --output localstack-cli-4.4.0-linux-arm64-onefile.tar.gz \
         --location https://github.com/localstack/localstack-cli/releases/download/v4.4.0/localstack-cli-4.4.0-linux-arm64-onefile.tar.gz
    sudo tar xvzf localstack-cli-4.4.0-linux-arm64-onefile.tar.gz -C /usr/local/bin
    rm localstack-cli-4.4.0-linux-arm64-onefile.tar.gz
else
    echo "✓ LocalStack CLI is already installed"
fi

# Install AWS CLI Local
echo "🌐 Installing AWS CLI Local..."
if ! command -v awslocal &> /dev/null; then
    uv tool install awscli-local
else
    echo "✓ AWS CLI Local is already installed"
fi

# Install Terraform
echo "🏗️  Installing Terraform..."
if ! command -v terraform &> /dev/null; then
    echo "📦 Adding HashiCorp GPG key and repository..."

    # Update package lists and install prerequisites
    sudo apt-get update
    sudo apt-get install -y gnupg software-properties-common

    # Add HashiCorp GPG key
    wget -O- https://apt.releases.hashicorp.com/gpg | \
    gpg --dearmor | \
    sudo tee /usr/share/keyrings/hashicorp-archive-keyring.gpg > /dev/null

    # Verify the key fingerprint
    gpg --no-default-keyring \
    --keyring /usr/share/keyrings/hashicorp-archive-keyring.gpg \
    --fingerprint

    # Add HashiCorp repository
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(grep -oP '(?<=UBUNTU_CODENAME=).*' /etc/os-release || lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/hashicorp.list

    # Update package lists and install Terraform
    sudo apt update
    sudo apt-get install terraform

    echo "✓ Terraform installed successfully"
else
    echo "✓ Terraform is already installed"
fi

# Install Oh My Zsh
echo "🐚 Installing Oh My Zsh..."
if [ ! -d "$HOME/.oh-my-zsh" ]; then
    # Install zsh if not already installed
    sudo apt-get install -y zsh

    # Install Oh My Zsh
    sh -c "$(curl -fsSL https://raw.github.com/ohmyzsh/ohmyzsh/master/tools/install.sh)" "" --unattended

    echo "✓ Oh My Zsh installed successfully"
else
    echo "✓ Oh My Zsh is already installed"
fi

# Install additional zsh plugins
echo "🔌 Installing zsh plugins..."

# Install zsh-autosuggestions plugin
if [ ! -d "${ZSH_CUSTOM:-$HOME/.oh-my-zsh/custom}/plugins/zsh-autosuggestions" ]; then
    git clone https://github.com/zsh-users/zsh-autosuggestions ${ZSH_CUSTOM:-$HOME/.oh-my-zsh/custom}/plugins/zsh-autosuggestions
    echo "✓ zsh-autosuggestions installed"
else
    echo "✓ zsh-autosuggestions already installed"
fi

# Install zsh-syntax-highlighting plugin
if [ ! -d "${ZSH_CUSTOM:-$HOME/.oh-my-zsh/custom}/plugins/zsh-syntax-highlighting" ]; then
    git clone https://github.com/zsh-users/zsh-syntax-highlighting.git ${ZSH_CUSTOM:-$HOME/.oh-my-zsh/custom}/plugins/zsh-syntax-highlighting
    echo "✓ zsh-syntax-highlighting installed"
else
    echo "✓ zsh-syntax-highlighting already installed"
fi

# Install zsh-completions plugin
if [ ! -d "${ZSH_CUSTOM:-$HOME/.oh-my-zsh/custom}/plugins/zsh-completions" ]; then
    git clone https://github.com/zsh-users/zsh-completions ${ZSH_CUSTOM:-$HOME/.oh-my-zsh/custom}/plugins/zsh-completions
    echo "✓ zsh-completions installed"
else
    echo "✓ zsh-completions already installed"
fi

# Configure Oh My Zsh
echo "⚙️  Configuring Oh My Zsh..."
cat > ~/.zshrc << 'EOF'
# Path to your oh-my-zsh installation.
export ZSH="$HOME/.oh-my-zsh"

# Set name of the theme to load
ZSH_THEME="amuse"

# Plugins to load
plugins=(
    git
    vscode
    zsh-autosuggestions
    zsh-syntax-highlighting
    zsh-completions
    docker
    npm
    python
    pip
    uv
)

# Load Oh My Zsh
source $ZSH/oh-my-zsh.sh

# User configuration
export PATH="$HOME/.local/bin:$PATH"

# Custom aliases
alias zshrc="sudo code $HOME/.zshrc"
alias c=clear
alias reload="zsh --login"
alias aws-env='eval "$(just aws)"'

# Load completions
autoload -U compinit && compinit
EOF

echo "✓ Oh My Zsh configured with amuse theme and plugins"

# Set zsh as default shell
echo "🐚 Setting zsh as default shell..."
if [ "$SHELL" != "/usr/bin/zsh" ] && [ "$SHELL" != "/bin/zsh" ]; then
    sudo chsh -s $(which zsh) $(whoami)
    echo "✓ Default shell changed to zsh (will take effect on next login)"
else
    echo "✓ zsh is already the default shell"
fi

# Add useful aliases to bashrc (for backward compatibility)
echo "🔧 Setting up shell aliases..."
if ! grep -q "alias aws-env=" ~/.bashrc; then
    echo 'alias aws-env='\''eval "$(just aws)"'\''' >> ~/.bashrc
    echo "✓ Added aws-env alias to ~/.bashrc"
else
    echo "✓ aws-env alias already exists in ~/.bashrc"
fi

# Verify installations
echo "✅ Verifying installations..."
localstack --version
awslocal --version
terraform --version

echo "🎉 DevContainer setup completed successfully!"
echo "💡 Tip: Use 'aws-env' to load AWS credentials from secrets.yaml into your shell"
