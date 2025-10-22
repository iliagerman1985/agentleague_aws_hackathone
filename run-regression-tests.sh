#!/bin/bash

# Regression Test Runner
# Runs only the main flow tests (@regression tagged) for faster feedback

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
BACKEND_PORT=9997
CLIENT_PORT=5889
TEST_DB_PATH="backend/test.db"

echo -e "${BLUE}🚀 Starting Regression Test Suite${NC}"
echo -e "${BLUE}Running main flow tests only for faster feedback${NC}"

# Function to cleanup processes
cleanup() {
    echo -e "\n${YELLOW}🧹 Cleaning up processes...${NC}"
    
    # Kill background processes
    if [[ -n $BACKEND_PID ]]; then
        kill $BACKEND_PID 2>/dev/null || true
        wait $BACKEND_PID 2>/dev/null || true
    fi
    
    if [[ -n $CLIENT_PID ]]; then
        kill $CLIENT_PID 2>/dev/null || true
        wait $CLIENT_PID 2>/dev/null || true
    fi
    
    # Remove test database
    if [[ -f "$TEST_DB_PATH" ]]; then
        rm -f "$TEST_DB_PATH"
        echo -e "${GREEN}✅ Test database cleaned up${NC}"
    fi
}

# Set up cleanup trap
trap cleanup EXIT

# Check if clean argument is provided
if [[ "$1" == "clean" ]]; then
    echo -e "${YELLOW}🧹 Cleaning up test artifacts...${NC}"
    cleanup
    echo -e "${GREEN}✅ Cleanup completed${NC}"
    exit 0
fi

# Set test environment variables
export APP_ENV=test
export NODE_ENV=test
export DATABASE_URL=sqlite:///./test_database.db

# Step 1: Start backend server first
echo -e "\n${BLUE}🔧 Starting backend server on port $BACKEND_PORT...${NC}"
cd backend
APP_ENV=test DATABASE_URL=sqlite:///./test_database.db python -m uvicorn app.main:app --host 0.0.0.0 --port $BACKEND_PORT --reload &
BACKEND_PID=$!
cd ..

# Wait for backend to be ready
echo -e "${YELLOW}⏳ Waiting for backend to be ready...${NC}"
for i in {1..30}; do
    if curl -s http://localhost:$BACKEND_PORT/api/v1/health > /dev/null; then
        echo -e "${GREEN}✅ Backend server is ready${NC}"
        break
    fi
    if [[ $i -eq 30 ]]; then
        echo -e "${RED}❌ Backend server failed to start${NC}"
        exit 1
    fi
    sleep 2
done

# Step 2: Setup test database after backend is ready
echo -e "\n${BLUE}📊 Setting up test database...${NC}"
cd backend
APP_ENV=test DATABASE_URL=sqlite:///./test_database.db python -m app.db.populate_test_db
if [[ $? -ne 0 ]]; then
    echo -e "${RED}❌ Failed to setup test database${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Test database ready${NC}"
cd ..

# Step 3: Start client server
echo -e "\n${BLUE}🌐 Starting client server on port $CLIENT_PORT...${NC}"
cd client
NODE_ENV=test npm run dev -- --port $CLIENT_PORT --mode test &
CLIENT_PID=$!
cd ..

# Wait for client to be ready
echo -e "${YELLOW}⏳ Waiting for client to be ready...${NC}"
for i in {1..30}; do
    if curl -s http://localhost:$CLIENT_PORT > /dev/null; then
        echo -e "${GREEN}✅ Client server is ready${NC}"
        break
    fi
    if [[ $i -eq 30 ]]; then
        echo -e "${RED}❌ Client server failed to start${NC}"
        exit 1
    fi
    sleep 1
done

# Step 4: Run regression tests
echo -e "\n${BLUE}🧪 Running regression tests...${NC}"
cd client

# Set environment variables for Playwright
export PLAYWRIGHT_BASE_URL="http://localhost:$CLIENT_PORT"
export NODE_ENV=test

# Run only regression tests
npx playwright test --config=playwright.regression.config.ts

TEST_EXIT_CODE=$?

cd ..

# Report results
if [[ $TEST_EXIT_CODE -eq 0 ]]; then
    echo -e "\n${GREEN}🎉 All regression tests passed!${NC}"
    echo -e "${GREEN}✅ Main application flow is working correctly${NC}"
else
    echo -e "\n${RED}❌ Some regression tests failed${NC}"
    echo -e "${YELLOW}💡 Run full test suite with './run-tests.sh' for detailed analysis${NC}"
fi

exit $TEST_EXIT_CODE
