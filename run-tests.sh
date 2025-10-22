#!/bin/bash
set -e

# Configuration
BACKEND_PORT=9997
CLIENT_PORT=5889
TEST_DB_FILE="backend/test_database.db"
BACKEND_PID=""
CLIENT_PID=""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Cleanup function
cleanup() {
    log_info "Cleaning up test environment..."
    
    # Kill backend process
    if [ ! -z "$BACKEND_PID" ] && kill -0 $BACKEND_PID 2>/dev/null; then
        log_info "Stopping backend server (PID: $BACKEND_PID)"
        kill $BACKEND_PID
        wait $BACKEND_PID 2>/dev/null || true
    fi
    
    # Kill client process
    if [ ! -z "$CLIENT_PID" ] && kill -0 $CLIENT_PID 2>/dev/null; then
        log_info "Stopping client server (PID: $CLIENT_PID)"
        kill $CLIENT_PID
        wait $CLIENT_PID 2>/dev/null || true
    fi
    
    # Kill any remaining processes on our ports
    if lsof -ti:$BACKEND_PORT >/dev/null 2>&1; then
        log_info "Killing remaining processes on port $BACKEND_PORT"
        kill -9 $(lsof -ti:$BACKEND_PORT) 2>/dev/null || true
    fi
    
    if lsof -ti:$CLIENT_PORT >/dev/null 2>&1; then
        log_info "Killing remaining processes on port $CLIENT_PORT"
        kill -9 $(lsof -ti:$CLIENT_PORT) 2>/dev/null || true
    fi
    
    # Remove test database
    if [ -f "$TEST_DB_FILE" ]; then
        log_info "Removing test database"
        rm -f "$TEST_DB_FILE"
    fi
    
    log_success "Cleanup completed"
}

# Check if port is available
check_port() {
    local port=$1
    if lsof -ti:$port >/dev/null 2>&1; then
        log_error "Port $port is already in use"
        lsof -ti:$port | xargs ps -p
        return 1
    fi
    return 0
}

# Wait for service to be ready
wait_for_service() {
    local url=$1
    local service_name=$2
    local max_attempts=30
    local attempt=1
    
    log_info "Waiting for $service_name to be ready at $url"
    
    while [ $attempt -le $max_attempts ]; do
        if curl -s -f "$url" > /dev/null 2>&1; then
            log_success "$service_name is ready"
            return 0
        fi
        
        if [ $attempt -eq $max_attempts ]; then
            log_error "$service_name failed to start within timeout"
            return 1
        fi
        
        log_info "Attempt $attempt/$max_attempts - waiting for $service_name..."
        sleep 2
        attempt=$((attempt + 1))
    done
    
    return 1
}

# Main test execution
main() {
    log_info "Starting comprehensive test suite"
    
    # Set test environment
    export APP_ENV=test
    export NODE_ENV=test
    
    # Check if ports are available
    if ! check_port $BACKEND_PORT; then
        log_error "Backend port $BACKEND_PORT is not available"
        exit 1
    fi
    
    if ! check_port $CLIENT_PORT; then
        log_error "Client port $CLIENT_PORT is not available"
        exit 1
    fi
    
    # Clean up existing test database
    if [ -f "$TEST_DB_FILE" ]; then
        log_info "Removing existing test database"
        rm -f "$TEST_DB_FILE"
    fi
    
    # Start backend server
    log_info "Starting backend server on port $BACKEND_PORT"
    cd backend
    APP_ENV=test DATABASE_URL=sqlite:///./test_database.db USE_MOCK_COGNITO=true USE_AWS_SECRET_MANAGER=false uvicorn app.main:app --host 0.0.0.0 --port $BACKEND_PORT --reload > ../backend.log 2>&1 &
    BACKEND_PID=$!
    cd ..
    
    # Wait for backend to be ready
    if ! wait_for_service "http://localhost:$BACKEND_PORT/api/v1/health" "Backend server"; then
        log_error "Backend server failed to start"
        cleanup
        exit 1
    fi
    
    # Populate test database
    log_info "Populating test database"
    if ! APP_ENV=test DATABASE_URL=sqlite:///./test_database.db USE_MOCK_COGNITO=true USE_AWS_SECRET_MANAGER=false uv run python -m shared_db.db.populate_test_db; then
        log_error "Failed to populate test database"
        cleanup
        exit 1
    fi
    
    # Start client server
    log_info "Starting client server on port $CLIENT_PORT"
    cd client
    npm run dev -- --port $CLIENT_PORT --mode test > ../client.log 2>&1 &
    CLIENT_PID=$!
    cd ..
    
    # Wait for client to be ready
    if ! wait_for_service "http://localhost:$CLIENT_PORT" "Client server"; then
        log_error "Client server failed to start"
        cleanup
        exit 1
    fi
    
    # Run tests
    log_info "Running Playwright tests"
    cd client
    export PLAYWRIGHT_BASE_URL="http://localhost:$CLIENT_PORT"
    
    if npx playwright test --reporter=html; then
        log_success "All tests passed!"
        test_result=0
    else
        log_error "Some tests failed"
        test_result=1
    fi
    
    cd ..
    
    # Show test results location
    log_info "Test results available at: client/test-results/html-report/index.html"
    
    return $test_result
}

# Handle script arguments
case "${1:-}" in
    "clean")
        log_info "Cleaning up test environment"
        cleanup
        ;;
    "")
        # Set up cleanup trap
        trap cleanup EXIT
        main
        ;;
    *)
        log_error "Unknown command: $1"
        echo "Usage: $0 [clean]"
        exit 1
        ;;
esac
