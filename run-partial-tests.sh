#!/bin/bash

# Partial test runner script for the Internal Assistant application
# This script sets up a clean test environment and runs specific UI tests

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
BACKEND_PORT=9997
CLIENT_PORT=5889
TEST_DB_FILE="backend/test_database.db"
BACKEND_PID=""
CLIENT_PID=""

# Function to print colored output
print_status() {
    echo -e "${BLUE}[TEST]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to cleanup processes and files
cleanup() {
    print_status "Cleaning up test environment..."

    # Kill backend process by PID if available
    if [ ! -z "$BACKEND_PID" ]; then
        print_status "Stopping backend server (PID: $BACKEND_PID)..."
        kill $BACKEND_PID 2>/dev/null || true
        wait $BACKEND_PID 2>/dev/null || true
    fi

    # Kill client process by PID if available
    if [ ! -z "$CLIENT_PID" ]; then
        print_status "Stopping client server (PID: $CLIENT_PID)..."
        kill $CLIENT_PID 2>/dev/null || true
        wait $CLIENT_PID 2>/dev/null || true
    fi

    # Also kill any processes running on test ports
    print_status "Checking for processes on test ports..."

    # Kill backend on port 9011
    BACKEND_PIDS=$(lsof -ti:$BACKEND_PORT 2>/dev/null || true)
    if [ ! -z "$BACKEND_PIDS" ]; then
        print_status "Killing backend processes on port $BACKEND_PORT..."
        echo $BACKEND_PIDS | xargs kill -9 2>/dev/null || true
    fi

    # Kill client on port 5179
    CLIENT_PIDS=$(lsof -ti:$CLIENT_PORT 2>/dev/null || true)
    if [ ! -z "$CLIENT_PIDS" ]; then
        print_status "Killing client processes on port $CLIENT_PORT..."
        echo $CLIENT_PIDS | xargs kill -9 2>/dev/null || true
    fi
    
    # Clean up test database file
    if [ -f "$TEST_DB_FILE" ]; then
        print_status "Removing test database file..."
        rm -f "$TEST_DB_FILE"
    fi
    
    print_success "Cleanup completed"
}

# Set up trap to cleanup on exit
trap cleanup EXIT

# Function to wait for service to be ready
wait_for_service() {
    local url=$1
    local service_name=$2
    local max_attempts=30
    local attempt=1
    
    print_status "Waiting for $service_name to be ready at $url..."
    
    while [ $attempt -le $max_attempts ]; do
        if curl -s -f "$url" > /dev/null 2>&1; then
            print_success "$service_name is ready!"
            return 0
        fi
        
        echo -n "."
        sleep 2
        attempt=$((attempt + 1))
    done
    
    print_error "$service_name failed to start within $((max_attempts * 2)) seconds"
    return 1
}

# Function to check if port is in use
check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        print_error "Port $port is already in use. Please stop the service using this port."
        exit 1
    fi
}

# Function to setup test environment
setup_test_environment() {
    print_status "Starting test environment setup..."
    
    # Check if required ports are available
    check_port $BACKEND_PORT
    check_port $CLIENT_PORT
    
    # Set environment variables for test mode
    export APP_ENV=test
    export NODE_ENV=test
    export VITE_API_URL="http://localhost:$BACKEND_PORT"
    
    # Start backend server with test configuration
    print_status "Starting backend server on port $BACKEND_PORT..."
    cd backend
    APP_ENV=test USE_MOCK_COGNITO=true USE_AWS_SECRET_MANAGER=false uvicorn app.main:app --host 0.0.0.0 --port $BACKEND_PORT --reload > ../backend_test.log 2>&1 &
    BACKEND_PID=$!
    cd ..
    
    # Wait for backend to be ready
    wait_for_service "http://localhost:$BACKEND_PORT/api/v1/health" "Backend server" || exit 1
    
    # Populate test database
    print_status "Populating test database with test users..."
    cd backend
    APP_ENV=test python -m app.db.populate_test_db || {
        print_error "Failed to populate test database"
        exit 1
    }
    cd ..
    print_success "Test database populated successfully"
    
    # Start client server with test configuration
    print_status "Starting client server on port $CLIENT_PORT..."
    cd client
    npm run dev -- --port $CLIENT_PORT --mode test > ../client_test.log 2>&1 &
    CLIENT_PID=$!
    cd ..
    
    # Wait for client to be ready
    wait_for_service "http://localhost:$CLIENT_PORT" "Client server" || exit 1
}

# Function to run tests based on type
run_tests() {
    local test_type=$1
    local test_pattern=$2
    
    print_status "Running Playwright tests ($test_type: $test_pattern)..."
    cd client
    
    # Set the base URL for tests to use the test client port
    export PLAYWRIGHT_BASE_URL="http://localhost:$CLIENT_PORT"
    
    # Run tests based on type
    case $test_type in
        "grep")
            npx playwright test -g "$test_pattern" --reporter=html
            ;;
        "file")
            npx playwright test "$test_pattern" --reporter=html
            ;;
        "suite")
            npx playwright test -g "$test_pattern" --reporter=html
            ;;
        *)
            print_error "Unknown test type: $test_type"
            exit 1
            ;;
    esac
    
    TEST_EXIT_CODE=$?
    cd ..

    # Report test results
    if [ $TEST_EXIT_CODE -eq 0 ]; then
        print_success "All tests completed successfully!"
    else
        print_warning "Some tests failed, but all tests were executed. Check the report for details."
    fi
    print_status "Test report available at: client/test-results/html-report/index.html"
    
    # Exit with the test result code
    exit $TEST_EXIT_CODE
}

# Main execution
main() {
    local test_type=$1
    local test_pattern=$2
    
    if [ -z "$test_type" ] || [ -z "$test_pattern" ]; then
        print_error "Usage: $0 <grep|file|suite> <pattern>"
        print_error "Examples:"
        print_error "  $0 grep \"validation errors\""
        print_error "  $0 file \"tests/mcp.spec.ts\""
        print_error "  $0 suite \"mcp\""
        exit 1
    fi
    
    setup_test_environment
    run_tests "$test_type" "$test_pattern"
}

# Run main function with all arguments
main "$@"
