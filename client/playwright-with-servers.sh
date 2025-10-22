#!/bin/bash

# Script to run Playwright tests with automatic server management
# This script is designed to work with the VS Code Playwright extension

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to check if servers are running
check_servers() {
    local backend_running=false
    local frontend_running=false
    
    if curl -s http://localhost:9997/health >/dev/null 2>&1; then
        backend_running=true
    fi
    
    if curl -s http://localhost:5889 >/dev/null 2>&1; then
        frontend_running=true
    fi
    
    if $backend_running && $frontend_running; then
        return 0
    else
        return 1
    fi
}

# Function to start servers if not running
ensure_servers_running() {
    if check_servers; then
        echo -e "${GREEN}✅ Test servers are already running${NC}"
        return 0
    fi
    
    echo -e "${YELLOW}🚀 Starting test servers...${NC}"
    cd ..
    just start-test-servers
    cd client
    
    # Wait a bit more to ensure servers are fully ready
    sleep 3
    
    if check_servers; then
        echo -e "${GREEN}✅ Test servers started successfully${NC}"
        return 0
    else
        echo -e "${RED}❌ Failed to start test servers${NC}"
        return 1
    fi
}

# Main execution
echo -e "${YELLOW}🧪 Playwright Test Runner with Server Management${NC}"

# Ensure servers are running
if ! ensure_servers_running; then
    echo -e "${RED}❌ Cannot run tests without servers${NC}"
    exit 1
fi

# Set environment variables for tests
export PLAYWRIGHT_BASE_URL="http://localhost:5174"
export USE_MEMORY_DB="true"

# Run Playwright with all passed arguments
echo -e "${GREEN}🎭 Running Playwright tests...${NC}"
npx playwright test "$@"

# Capture the exit code
exit_code=$?

echo -e "${YELLOW}📊 Test execution completed with exit code: $exit_code${NC}"

# Note: We don't stop servers here as they might be needed for debugging
# or running additional tests. Use 'just stop-test-servers' manually when done.

exit $exit_code
