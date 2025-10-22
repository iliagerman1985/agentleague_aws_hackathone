# Aliases
alias install := sync

# Install python dependencies using uv
sync:
    uv sync --all-packages

# Upgrade python dependencies
upgrade:
    uv sync --upgrade

# Install pre-commit hooks
pre_commit_setup:
    uv run pre-commit install

# Install python dependencies and pre-commit hooks
setup: sync pre_commit_setup
    cd client && npm install

# Run pre-commit on all files
pre_commit:
    uv run pre-commit run -a

# Run pytest using uv
test:
    uv run pytest

tsc:
    cd client && npm run tsc

# Lint code with ruff
lint folder="." fix="":
    uv run ruff check {{folder}} {{fix}}

# Format code with ruff
format folder=".":
    uv run ruff format {{folder}}

# Type check with pyright
pyright directory=".":
    uv run pyright --threads 8 {{directory}}

# Generate a new database-agnostic migration that works with both SQLite and PostgreSQL
generate_migration message="Database-agnostic migration":
    uv run --package shared_db python -m shared_db.db.create_agnostic_migration -m "{{message}}"

# Generate a legacy Alembic migration (use only if you need database-specific features)
generate_legacy_migration db_type="core":
    uv run --package shared_db alembic -c libs/shared_db/alembic.ini revision --autogenerate

# Apply Alembic migrations (uv monorepo version)
migrate db_type="core":
    uv run --package shared_db alembic -c libs/shared_db/alembic.ini upgrade head

# Downgrade database by one migration
downgrade db_type="core":
    uv run --package shared_db alembic -c libs/shared_db/alembic.ini downgrade -1

# Reset database: drop all tables, delete migrations, and recreate fresh
reset-db:
    @echo "🗑️  Resetting database and migrations..."
    @echo "🔐 Using local secrets (USE_AWS_SECRET_MANAGER=false)"
    @echo "🧹 Cleaning up migration files..."
    uv run python -c "import glob, os; [os.remove(f) for f in glob.glob('libs/shared_db/alembic/versions/*.py') if not f.endswith('__init__.py')]"
    @echo "🗑️  Dropping all database tables..."
    USE_AWS_SECRET_MANAGER=false just drop_db
    @echo "🔄 Generating fresh database-agnostic migration..."
    USE_AWS_SECRET_MANAGER=false just generate_migration "Initial migration with all models"
    @echo "⬆️  Applying fresh migration..."
    USE_AWS_SECRET_MANAGER=false uv run --package shared_db alembic -c libs/shared_db/alembic.ini upgrade head
    @echo "✅ Database reset complete!"

# Clear database: delete all table data but keep table structure and migrations intact
clear_db:
    @echo "🧹 Clearing database data (keeping table structure and migrations)..."
    @echo "🗑️  Deleting all table data..."
    USE_AWS_SECRET_MANAGER=false uv run --package shared_db python -m shared_db.db.reset_database --clear-data
    @echo "✅ Database data cleared! Table structure and migrations preserved."

# Drop database: drop all tables but keep migrations and database intact
drop_db:
    @echo "🗑️  Dropping all database tables (keeping migrations and database)..."
    @echo "💥 Dropping all tables..."
    USE_AWS_SECRET_MANAGER=false uv run --package shared_db python -m shared_db.db.reset_database --drop-tables
    @echo "✅ Database tables dropped! Database and migrations preserved."

# Populate database with sample data (uv version)
populate_db:
    uv run --package shared_db python -m shared_db.db.populate_db

# Decode a TSID string to a long integer
decode-tsid tsid_string:
    uv run --package shared_db python -m shared_db.db.decode_tsid {{tsid_string}}

local_dev:
    cd local_dev && docker compose up -d

# Run the backend server (uv version)
run-backend:
    uv run --package backend uvicorn app.main:app --host 0.0.0.0 --port 9998 --reload --reload-dir backend --reload-dir libs

# Run the frontend client
run-client:
    cd client && npm start

# Run the agentcore server
run-agentcore:
    uv run --package agentcore-server uvicorn agentcore.main:app --host 0.0.0.0 --port 8765 --reload --reload-dir agentcore --reload-dir libs

# Run all services
run:
    just run-backend & just run-client & just run-agentcore

# Build dockerfile for specific target
build target:
    docker build -t packages/{{target}} --build-arg PACKAGE={{target}} .

# Start local development environment
local_dev_up:
    docker compose up -d --remove-orphans

# Stop local development environment
local_dev_down:
    docker compose down

# Create SQS queues for local development
create_sqs:
    awslocal sqs create-queue --queue-name game-queue
    awslocal sqs create-queue --queue-name game-analysis-queue

# Purge SQS queues
purge_sqs:
    awslocal sqs purge-queue --queue-url http://0.0.0.0:4566/000000000000/game-queue --region=us-east-1
    awslocal sqs purge-queue --queue-url http://0.0.0.0:4566/000000000000/game-analysis-queue --region=us-east-1

# E2E Test commands (client integration tests using actual backend)
# Note: Main E2E commands are defined below in the "E2E Test Commands - Main Interface" section

# Populate test database (uv version)
populate-test-db:
    echo "🔧 Running database migrations..."
    APP_ENV=test DATABASE_URL=sqlite:///./test_database.db uv run --package shared_db alembic -c libs/shared_db/alembic.ini upgrade head
    echo "📝 Populating test data..."
    APP_ENV=test DATABASE_URL=sqlite:///./test_database.db uv run python -m shared_db.db.populate_test_db

# Clean up test database
cleanup-test-db:
    cd backend && APP_ENV=test python -m app.db.populate_test_db --cleanup

# Clean up EC2 instance (Docker images, logs, etc.)
cleanup-ec2:
    #!/bin/bash
    set -e
    echo "🧹 Running EC2 cleanup via SSH..."

    # Get EC2 instance IP
    INSTANCE_IP=$(aws ec2 describe-instances \
        --filters "Name=tag:Name,Values=agentleague-*instance*" "Name=instance-state-name,Values=running" \
        --query 'Reservations[0].Instances[0].PublicIpAddress' \
        --output text --region us-east-1)

    if [ "$INSTANCE_IP" = "None" ] || [ -z "$INSTANCE_IP" ]; then
        echo "❌ No running EC2 instance found"
        exit 1
    fi

    echo "💻 Connecting to EC2 instance: $INSTANCE_IP"

    # Run the cleanup script on the EC2 instance
    ssh -i terraform/dev.pem -o StrictHostKeyChecking=no ubuntu@$INSTANCE_IP 'bash -s' < scripts/cleanup-ec2.sh

    echo "✅ EC2 cleanup completed!"

# Debug EC2 deployment issues
debug-ec2:
    #!/bin/bash
    set -e
    echo "🔍 Debugging EC2 deployment..."

    # Get EC2 instance IP
    INSTANCE_IP=$(aws ec2 describe-instances \
        --filters "Name=tag:Name,Values=agentleague-*instance*" "Name=instance-state-name,Values=running" \
        --query 'Reservations[0].Instances[0].PublicIpAddress' \
        --output text --region us-east-1)

    if [ "$INSTANCE_IP" = "None" ] || [ -z "$INSTANCE_IP" ]; then
        echo "❌ No running EC2 instance found"
        exit 1
    fi

    echo "💻 Connecting to EC2 instance: $INSTANCE_IP"

    # Run comprehensive debugging
    ssh -i terraform/dev.pem -o StrictHostKeyChecking=no ubuntu@$INSTANCE_IP << 'EOF'
        echo "🏠 System Info:"
        echo "Architecture: $(uname -m)"
        echo "OS: $(cat /etc/os-release | grep PRETTY_NAME)"
        echo ""

        echo "🐳 Docker Info:"
        sudo docker version
        echo ""

        echo "📊 Container Status:"
        sudo docker ps -a
        echo ""

        echo "🖼️ Images:"
        sudo docker images
        echo ""

        echo "📝 Recent Container Logs:"
        for container in agentleague-backend agentleague-frontend agentleague-postgres; do
            if sudo docker ps -a --filter "name=$container" --quiet | grep -q .; then
                echo "=== $container logs ==="
                sudo docker logs $container --tail 20 2>&1 || echo "No logs for $container"
                echo ""
            fi
        done

        echo "📊 System Resources:"
        echo "Disk usage:"
        df -h
        echo "Memory:"
        free -h
        echo "Docker system:"
        sudo docker system df
    EOF

    echo "✅ Debug completed!"

# List Docker volumes on EC2 instance
list-ec2-volumes:
    #!/bin/bash
    set -e
    echo "🗂️  Listing Docker volumes on EC2..."

    # Get EC2 instance IP
    INSTANCE_IP=$(aws ec2 describe-instances \
        --filters "Name=tag:Name,Values=agentleague-*instance*" "Name=instance-state-name,Values=running" \
        --query 'Reservations[0].Instances[0].PublicIpAddress' \
        --output text --region us-east-1)

    if [ "$INSTANCE_IP" = "None" ] || [ -z "$INSTANCE_IP" ]; then
        echo "❌ No running EC2 instance found"
        exit 1
    fi

    echo "💻 Connecting to EC2 instance: $INSTANCE_IP"

    # List Docker volumes
    ssh -i terraform/dev.pem -o StrictHostKeyChecking=no ubuntu@$INSTANCE_IP << 'EOF'
        echo "📊 Docker volumes:"
        sudo docker volume ls
        echo ""
        echo "📊 Volume details:"
        sudo docker volume ls -q | xargs -I {} sudo docker volume inspect {} || true
        echo ""
        echo "📊 Disk usage by volume:"
        sudo docker volume ls -q | xargs -I {} sudo du -sh /var/lib/docker/volumes/{} 2>/dev/null || true
    EOF

# Playwright Test Commands with automatic server startup

# Start test servers (backend + frontend)
start-test-servers:
    #!/bin/bash
    set -e

    # Kill any existing processes on test ports
    echo "🛑 Ensuring no servers are running on test ports..."
    pkill -f "uvicorn.*:9997" || true
    pkill -f "vite.*5889" || true
    # Force kill any processes on test ports
    lsof -ti:9997 | xargs kill -9 2>/dev/null || true
    lsof -ti:5889 | xargs kill -9 2>/dev/null || true
    sleep 2

    # Verify ports are actually free
    echo "🔍 Verifying ports 9997 and 5889 are free..."
    for i in {1..10}; do
        if ! lsof -i:9997 >/dev/null 2>&1 && ! lsof -i:5889 >/dev/null 2>&1; then
            echo "✅ Ports are free"
            break
        fi
        if [ $i -eq 10 ]; then
            echo "❌ Failed to free ports after 10 attempts"
            exit 1
        fi
        echo "⏳ Waiting for ports to be freed... (attempt $i/10)"
        sleep 1
    done

    echo "🚀 Starting backend server with MOCK Cognito on port 9997..."

    # Clean up old test database to ensure fresh schema
    rm -f test_database.db
    echo "🗑️  Removed old test database"

    # Start backend with test configuration (no AWS Secrets Manager)
    env APP_ENV=test DATABASE_URL=sqlite:///./test_database.db USE_MOCK_COGNITO=true USE_AWS_SECRET_MANAGER=false uv run --package backend uvicorn app.main:app --host 0.0.0.0 --port 9997 --reload --reload-dir backend --reload-dir libs &
    BACKEND_PID=$!

    echo "⏳ Waiting for backend to be ready..."
    for i in {1..30}; do
        if curl -s http://localhost:9997/health >/dev/null 2>&1; then
            echo "✅ Backend ready and responding"
            break
        fi
        if [ $i -eq 30 ]; then
            echo "❌ Backend failed to start after 30 seconds"
            echo "Backend process status:"
            ps aux | grep $BACKEND_PID || echo "Backend process not found"
            exit 1
        fi
        echo "⏳ Waiting for backend... (attempt $i/30)"
        sleep 1
    done

    echo "🌐 Starting frontend server on port 5889..."
    cd client && NODE_ENV=test VITE_API_URL=http://localhost:9997 VITE_COGNITO_CALLBACK_URL=http://localhost:5889/auth/callback npm run dev -- --mode test --host 0.0.0.0 --port 5889 &
    CLIENT_PID=$!
    cd ..

    echo "⏳ Waiting for frontend to be ready..."
    for i in {1..30}; do
        if curl -s http://localhost:5889 >/dev/null 2>&1; then
            echo "✅ Frontend ready and responding"
            break
        fi
        if [ $i -eq 30 ]; then
            echo "❌ Frontend failed to start after 30 seconds"
            echo "Frontend process status:"
            ps aux | grep $CLIENT_PID || echo "Frontend process not found"
            exit 1
        fi
        echo "⏳ Waiting for frontend... (attempt $i/30)"
        sleep 1
    done

    echo "📊 Setting up test database..."
    echo "🔧 SQLite will be initialized automatically by FastAPI startup (using create_all)"
    echo "📝 Populating test data..."
    cd /workspaces/agentleague && env APP_ENV=test DATABASE_URL=sqlite:///./test_database.db USE_AWS_SECRET_MANAGER=false uv run python -m shared_db.db.populate_test_db
    echo "✅ Test database ready"

    echo "🎉 Test servers are running!"
    echo "Backend: http://localhost:9997"
    echo "Frontend: http://localhost:5889"
    echo ""
    echo "To stop servers: just stop-test-servers"

# Start test servers in local mode (no AWS Secrets Manager)
start-test-servers-local:
    #!/bin/bash
    set -e

    # Kill any existing processes on test ports
    echo "🛑 Ensuring no servers are running on test ports..."
    pkill -f "uvicorn.*:9997" || true
    pkill -f "vite.*5889" || true
    # Force kill any processes on test ports
    lsof -ti:9997 | xargs kill -9 2>/dev/null || true
    lsof -ti:5889 | xargs kill -9 2>/dev/null || true
    sleep 2

    # Verify ports are actually free
    echo "🔍 Verifying ports 9997 and 5889 are free..."
    for i in {1..10}; do
        if ! lsof -i:9997 >/dev/null 2>&1 && ! lsof -i:5889 >/dev/null 2>&1; then
            echo "✅ Ports are free"
            break
        fi
        if [ $i -eq 10 ]; then
            echo "❌ Failed to free ports after 10 attempts"
            exit 1
        fi
        echo "⏳ Waiting for ports to be freed... (attempt $i/10)"
        sleep 1
    done

    echo "🚀 Starting backend server in LOCAL mode (no AWS Secrets Manager)..."

    # Clean up old test database to ensure fresh schema
    rm -f test_database.db
    echo "🗑️  Removed old test database"

    # Start backend with local configuration (no AWS Secrets Manager)
    env APP_ENV=test DATABASE_URL=sqlite:///./test_database.db USE_MOCK_COGNITO=true USE_AWS_SECRET_MANAGER=false uv run --package backend uvicorn app.main:app --host 0.0.0.0 --port 9997 --reload --reload-dir backend --reload-dir libs &
    BACKEND_PID=$!

    echo "⏳ Waiting for backend to be ready..."
    for i in {1..30}; do
        if curl -s http://localhost:9997/health >/dev/null 2>&1; then
            echo "✅ Backend ready and responding"
            break
        fi
        if [ $i -eq 30 ]; then
            echo "❌ Backend failed to start after 30 seconds"
            echo "Backend process status:"
            ps aux | grep $BACKEND_PID || echo "Backend process not found"
            exit 1
        fi
        echo "⏳ Waiting for backend... (attempt $i/30)"
        sleep 1
    done

    echo "🌐 Starting frontend server on port 5889..."
    cd client && NODE_ENV=test VITE_API_URL=http://localhost:9997 VITE_COGNITO_CALLBACK_URL=http://localhost:5889/auth/callback npm run dev -- --mode test --host 0.0.0.0 --port 5889 &
    CLIENT_PID=$!
    cd ..

    echo "⏳ Waiting for frontend to be ready..."
    for i in {1..30}; do
        if curl -s http://localhost:5889 >/dev/null 2>&1; then
            echo "✅ Frontend ready and responding"
            break
        fi
        if [ $i -eq 30 ]; then
            echo "❌ Frontend failed to start after 30 seconds"
            echo "Frontend process status:"
            ps aux | grep $CLIENT_PID || echo "Frontend process not found"
            exit 1
        fi
        echo "⏳ Waiting for frontend... (attempt $i/30)"
        sleep 1
    done

    echo "📊 Setting up test database..."
    echo "🔧 SQLite will be initialized automatically by FastAPI startup (using create_all)"
    echo "📝 Populating test data..."
    cd /workspaces/agentleague && env APP_ENV=test DATABASE_URL=sqlite:///./test_database.db USE_AWS_SECRET_MANAGER=false uv run python -m shared_db.db.populate_test_db
    echo "✅ Test database ready"

    echo "🎉 Test servers are running in LOCAL mode!"
    echo "Backend: http://localhost:9997"
    echo "Frontend: http://localhost:5889"
    echo ""
    echo "To stop servers: just stop-test-servers"

# Stop test servers
stop-test-servers:
    #!/bin/bash
    echo "🛑 Stopping test servers..."
    pkill -f "uvicorn.*:9997" || true
    pkill -f "vite.*5889" || true
    # Force kill any processes on test ports
    lsof -ti:9997 | xargs kill -9 2>/dev/null || true
    lsof -ti:5889 | xargs kill -9 2>/dev/null || true

    # Verify servers are actually stopped
    echo "🔍 Verifying servers are stopped..."
    for i in {1..10}; do
        if ! lsof -i:9997 >/dev/null 2>&1 && ! lsof -i:5889 >/dev/null 2>&1; then
            echo "✅ Test servers stopped and ports are free"
            break
        fi
        if [ $i -eq 10 ]; then
            echo "⚠️  Warning: Some processes may still be running on test ports"
            lsof -i:9997 2>/dev/null || true
            lsof -i:5889 2>/dev/null || true
        fi
        echo "⏳ Waiting for servers to stop... (attempt $i/10)"
        sleep 1
    done

# # Start test servers with real Cognito (uses development environment)
# start-test-servers-real-cognito:
#     #!/bin/bash
#     set -e

#     # Kill any existing processes on test ports
#     pkill -f "uvicorn.*:9997" || true
#     pkill -f "vite.*5889" || true
#     sleep 2

#     echo "🚀 Starting backend server with REAL Cognito (development env) on port 9997..."
#     # Use development environment which has real Cognito configured
#     APP_ENV=development uv run --package backend uvicorn app.main:app --host 0.0.0.0 --port 9997 --reload &
#     BACKEND_PID=$!

#     echo "⏳ Waiting for backend to be ready..."
#     timeout 30 bash -c 'until curl -s http://localhost:9997/health > /dev/null; do sleep 1; done' || (echo "❌ Backend failed to start" && exit 1)
#     echo "✅ Backend ready"

#     echo "🌐 Starting frontend server on port 5889..."
#     cd client && VITE_API_URL=http://localhost:9997 npm run dev -- --host 0.0.0.0 --port 5889 &
#     CLIENT_PID=$!
#     cd ..

#     echo "⏳ Waiting for frontend to be ready..."
#     timeout 30 bash -c 'until curl -s http://localhost:5889 > /dev/null; do sleep 1; done' || (echo "❌ Frontend failed to start" && exit 1)
#     echo "✅ Frontend ready"

#     echo "📊 Setting up development database for testing..."
#     echo "🔧 Running database migrations..."
#     cd /workspaces/agentleague && APP_ENV=development uv run --package shared_db alembic -c libs/shared_db/alembic.ini upgrade head
#     echo "📝 Populating test data (real Cognito users already exist)..."
#     echo "✅ Development database ready"

#     echo "🎉 Test servers are running with REAL Cognito (development environment)!"
#     echo "Backend: http://localhost:9997"
#     echo "Frontend: http://localhost:5889"
#     echo ""
#     echo "To stop servers: just stop-test-servers"

# # E2E Test Commands - Main Interface

# Run E2E tests (all tests or specific suite) with optional platform
test-e2e suite="all" *args="":
    #!/bin/bash
    set -e

    # Load secrets for E2E tests (local secrets.yaml or AWS Secrets Manager)
    echo "🔐 Loading secrets for E2E tests..."
    just _load-test-secrets

    # Create timestamp-based test results directory
    TIMESTAMP=$(date +"%d-%m-%y-%H-%M")
    TEST_RESULTS_ROOT="test_results"
    mkdir -p "$TEST_RESULTS_ROOT"

    # Parse platform argument
    PLATFORM=""
    PLATFORM_SUFFIX=""
    for arg in {{args}}; do
        if [[ "$arg" == "--platform" ]]; then
            PLATFORM_FLAG=true
        elif [[ "$PLATFORM_FLAG" == "true" ]]; then
            case "$arg" in
                "mobile"|"Mobile Chrome")
                    PLATFORM="Mobile Chrome"
                    PLATFORM_SUFFIX="MOBILE"
                    ;;
                "desktop"|"chrome"|"chromium")
                    PLATFORM="chromium"
                    PLATFORM_SUFFIX="DESKTOP"
                    ;;
                *)
                    echo "❌ Unknown platform: $arg"
                    echo "Available platforms: mobile, desktop, chrome, chromium"
                    exit 1
                    ;;
            esac
            PLATFORM_FLAG=false
        fi
    done

    # If no platform specified, run both mobile and desktop
    if [[ -z "$PLATFORM" ]]; then
        PLATFORM_SUFFIX="BOTH"
    fi

    # Create final results directory
    FINAL_RESULTS_DIR="$TEST_RESULTS_ROOT/$TIMESTAMP-$PLATFORM_SUFFIX"
    mkdir -p "$FINAL_RESULTS_DIR"

    case "{{suite}}" in
        "all")
            trap 'just stop-test-servers' EXIT
            echo "🧪 Running All E2E Tests (Mock + Real Cognito)"

            # First run all mock Cognito tests (excluding real-cognito tagged tests)
            echo "📋 Phase 1: Running Mock Cognito Tests"
            just start-test-servers

            if [[ -z "$PLATFORM" ]]; then
                # Run both mobile and desktop
                cd client && PLAYWRIGHT_WORKERS=1 PLAYWRIGHT_BASE_URL=http://localhost:5889 USE_MEMORY_DB=true npx playwright test --config=playwright.just.config.ts --grep-invert "@real-cognito"
            else
                # Run specific platform
                cd client && PLAYWRIGHT_WORKERS=1 PLAYWRIGHT_BASE_URL=http://localhost:5889 USE_MEMORY_DB=true npx playwright test --config=playwright.just.config.ts --project="$PLATFORM" --grep-invert "@real-cognito"
            fi

            just stop-test-servers

            # Copy results to timestamped directory
            echo "📁 Copying test results to $FINAL_RESULTS_DIR..."
            cp -r client/test-results/* "$FINAL_RESULTS_DIR/" 2>/dev/null || true

            # Then run real Cognito tests
            # echo "📋 Phase 2: Running Real Cognito Tests"
            # just start-test-servers-real-cognito
            # cd client && PLAYWRIGHT_BASE_URL=http://localhost:5889 npx playwright test --config=playwright.just.config.ts --grep "@real-cognito"
            # just stop-test-servers

            echo "📊 Test report stored at: $FINAL_RESULTS_DIR/html-report/index.html"
            echo "📁 Test artifacts stored in: $FINAL_RESULTS_DIR/"
            ;;
        "local")
            trap 'just stop-test-servers' EXIT
            echo "🧪 Running E2E Tests in Local Mode (No AWS Secrets Manager)"

            # Run tests with local configuration (no AWS Secrets Manager)
            echo "📋 Running Local E2E Tests"
            just start-test-servers-local

            if [[ -z "$PLATFORM" ]]; then
                # Run both mobile and desktop
                cd client && PLAYWRIGHT_WORKERS=1 PLAYWRIGHT_BASE_URL=http://localhost:5889 USE_MEMORY_DB=true npx playwright test --config=playwright.just.config.ts --grep-invert "@real-cognito"
            else
                # Run specific platform
                cd client && PLAYWRIGHT_WORKERS=1 PLAYWRIGHT_BASE_URL=http://localhost:5889 USE_MEMORY_DB=true npx playwright test --config=playwright.just.config.ts --project="$PLATFORM" --grep-invert "@real-cognito"
            fi

            just stop-test-servers

            # Copy results to timestamped directory
            echo "📁 Copying test results to $FINAL_RESULTS_DIR..."
            cp -r client/test-results/* "$FINAL_RESULTS_DIR/" 2>/dev/null || true

            echo "📊 Test report stored at: $FINAL_RESULTS_DIR/html-report/index.html"
            echo "📁 Test artifacts stored in: $FINAL_RESULTS_DIR/"
            ;;
        "login")
            trap 'just stop-test-servers' EXIT
            echo "🧪 Running Login Flow Tests (Mock + Real Cognito)"

            # Run mock Cognito login tests
            echo "📋 Phase 1: Mock Cognito Login Tests"
            just start-test-servers

            if [[ -z "$PLATFORM" ]]; then
                # Run both mobile and desktop
                cd client && PLAYWRIGHT_WORKERS=1 PLAYWRIGHT_BASE_URL=http://localhost:5889 USE_MEMORY_DB=true npx playwright test --config=playwright.just.config.ts --grep "login" --grep-invert "@real-cognito"
            else
                # Run specific platform
                cd client && PLAYWRIGHT_WORKERS=1 PLAYWRIGHT_BASE_URL=http://localhost:5889 USE_MEMORY_DB=true npx playwright test --config=playwright.just.config.ts --project="$PLATFORM" --grep "login" --grep-invert "@real-cognito"
            fi

            just stop-test-servers

            # Copy results to timestamped directory
            echo "📁 Copying test results to $FINAL_RESULTS_DIR..."
            cp -r client/test-results/* "$FINAL_RESULTS_DIR/" 2>/dev/null || true

            echo "📊 Test report stored at: $FINAL_RESULTS_DIR/html-report/index.html"
            echo "📁 Test artifacts stored in: $FINAL_RESULTS_DIR/"
            ;;
        "registration")
            just _run-e2e-suite "registration" "Registration Flow Tests"
            ;;
        "regression")
            PLAYWRIGHT_WORKERS=10 just _run-e2e-suite "@regression" "Regression Tests (Critical)"
            ;;
        "tools")
            just _run-suite-with-platform "tools/" "Tools Tests (CRUD + Vibe Coding)" "$PLATFORM"
            ;;
        "vibe-coding")
            just _run-suite-with-platform "tools/vibe-coding" "Vibe Coding Tests" "$PLATFORM"
            ;;
        "tools-crud")
            just _run-suite-with-platform "tools/tools-crud" "Tools CRUD Tests" "$PLATFORM"
            ;;
        "llm")
            just _run-suite-with-platform "llm/" "LLM Integration Tests (All Providers)" "$PLATFORM"
            ;;
        "llm-crud")
            just _run-suite-with-platform "llm/llm-crud" "LLM CRUD Tests (All Providers)" "$PLATFORM"
            ;;
        "llm-multi-provider")
            just _run-suite-with-platform "llm/llm-multi-provider" "LLM Multi-Provider API Tests" "$PLATFORM"
            ;;
        "llm-selection")
            just _run-suite-with-platform "llm/llm-selection" "LLM Selection UI Tests" "$PLATFORM"
            ;;
        # "real-cognito")
        #     just _run-e2e-suite-real-cognito "@real-cognito" "Real Cognito Integration Tests"
        #     ;;
        "list")
            just test-e2e-list
            ;;
        *)
            echo "❌ Unknown test suite: {{suite}}"
            echo "Run 'just test-e2e list' to see available suites"
            exit 1
            ;;
    esac

# Run specific E2E test file with timestamped results
test-e2e-file file *args="":
    #!/bin/bash
    set -e

    # Load secrets for E2E tests
    echo "🔐 Loading secrets for E2E tests..."
    just _load-test-secrets

    # Create timestamp-based test results directory
    TIMESTAMP=$(date +"%d-%m-%y-%H-%M")
    TEST_RESULTS_ROOT="test_results"
    mkdir -p "$TEST_RESULTS_ROOT"

    # Parse platform argument
    PLATFORM=""
    PLATFORM_SUFFIX=""
    for arg in {{args}}; do
        if [[ "$arg" == "--platform" ]]; then
            PLATFORM_FLAG=true
        elif [[ "$PLATFORM_FLAG" == "true" ]]; then
            case "$arg" in
                "mobile"|"Mobile Chrome")
                    PLATFORM="Mobile Chrome"
                    PLATFORM_SUFFIX="MOBILE"
                    ;;
                "desktop"|"chrome"|"chromium")
                    PLATFORM="chromium"
                    PLATFORM_SUFFIX="DESKTOP"
                    ;;
                *)
                    echo "❌ Unknown platform: $arg"
                    echo "Available platforms: mobile, desktop, chrome, chromium"
                    exit 1
                    ;;
            esac
            PLATFORM_FLAG=false
        fi
    done

    # If no platform specified, run both mobile and desktop
    if [[ -z "$PLATFORM" ]]; then
        PLATFORM_SUFFIX="BOTH"
    fi

    # Create final results directory
    FINAL_RESULTS_DIR="$TEST_RESULTS_ROOT/$TIMESTAMP-$PLATFORM_SUFFIX"
    mkdir -p "$FINAL_RESULTS_DIR"

    trap 'just stop-test-servers' EXIT
    echo "🧪 Running E2E Test File: {{file}}"

    echo "🗄️ Cleaning test database before starting..."
    rm -f test_database.db || true
    just start-test-servers

    if [[ -z "$PLATFORM" ]]; then
        # Run both mobile and desktop
        cd client && PLAYWRIGHT_WORKERS=1 PLAYWRIGHT_BASE_URL=http://localhost:5889 USE_MEMORY_DB=true npx playwright test --config=playwright.just.config.ts "{{file}}"
    else
        # Run specific platform
        cd client && PLAYWRIGHT_WORKERS=1 PLAYWRIGHT_BASE_URL=http://localhost:5889 USE_MEMORY_DB=true npx playwright test --config=playwright.just.config.ts --project="$PLATFORM" "{{file}}"
    fi

    just stop-test-servers

    # Copy results to timestamped directory
    echo "📁 Copying test results to $FINAL_RESULTS_DIR..."
    cp -r client/test-results/* "$FINAL_RESULTS_DIR/" 2>/dev/null || true

    echo "📊 Test report stored at: $FINAL_RESULTS_DIR/html-report/index.html"
    echo "📁 Test artifacts stored in: $FINAL_RESULTS_DIR/"

# Run E2E tests matching a pattern with timestamped results
test-e2e-grep pattern *args="":
    #!/bin/bash
    set -e

    # Load secrets for E2E tests
    echo "🔐 Loading secrets for E2E tests..."
    just _load-test-secrets

    # Create timestamp-based test results directory
    TIMESTAMP=$(date +"%d-%m-%y-%H-%M")
    TEST_RESULTS_ROOT="test_results"
    mkdir -p "$TEST_RESULTS_ROOT"

    # Parse platform argument
    PLATFORM=""
    PLATFORM_SUFFIX=""
    for arg in {{args}}; do
        if [[ "$arg" == "--platform" ]]; then
            PLATFORM_FLAG=true
        elif [[ "$PLATFORM_FLAG" == "true" ]]; then
            case "$arg" in
                "mobile"|"Mobile Chrome")
                    PLATFORM="Mobile Chrome"
                    PLATFORM_SUFFIX="MOBILE"
                    ;;
                "desktop"|"chrome"|"chromium")
                    PLATFORM="chromium"
                    PLATFORM_SUFFIX="DESKTOP"
                    ;;
                *)
                    echo "❌ Unknown platform: $arg"
                    echo "Available platforms: mobile, desktop, chrome, chromium"
                    exit 1
                    ;;
            esac
            PLATFORM_FLAG=false
        fi
    done

    # If no platform specified, run both mobile and desktop
    if [[ -z "$PLATFORM" ]]; then
        PLATFORM_SUFFIX="BOTH"
    fi

    # Create final results directory
    FINAL_RESULTS_DIR="$TEST_RESULTS_ROOT/$TIMESTAMP-$PLATFORM_SUFFIX"
    mkdir -p "$FINAL_RESULTS_DIR"

    trap 'just stop-test-servers' EXIT
    echo "🧪 Running E2E Tests matching pattern: {{pattern}}"

    echo "🗄️ Cleaning test database before starting..."
    rm -f test_database.db || true
    just start-test-servers

    if [[ -z "$PLATFORM" ]]; then
        # Run both mobile and desktop
        cd client && PLAYWRIGHT_WORKERS=1 PLAYWRIGHT_BASE_URL=http://localhost:5889 USE_MEMORY_DB=true npx playwright test --config=playwright.just.config.ts -g "{{pattern}}"
    else
        # Run specific platform
        cd client && PLAYWRIGHT_WORKERS=1 PLAYWRIGHT_BASE_URL=http://localhost:5889 USE_MEMORY_DB=true npx playwright test --config=playwright.just.config.ts --project="$PLATFORM" -g "{{pattern}}"
    fi

    just stop-test-servers

    # Copy results to timestamped directory
    echo "📁 Copying test results to $FINAL_RESULTS_DIR..."
    cp -r client/test-results/* "$FINAL_RESULTS_DIR/" 2>/dev/null || true

    echo "📊 Test report stored at: $FINAL_RESULTS_DIR/html-report/index.html"
    echo "📁 Test artifacts stored in: $FINAL_RESULTS_DIR/"

# List available E2E test suites
test-e2e-list:
    echo "📋 Available E2E Test Suites:"
    echo ""
    echo "🔐 Authentication:"
    echo "  login        - Login flow tests (mock + real Cognito)"
    echo "  registration - Registration flow tests (mock Cognito only)"
    echo ""
    echo "🤖 LLM Integration:"
    echo "  llm               - All LLM integration tests (all providers)"
    echo "  llm-crud          - LLM CRUD operations (OpenAI, Anthropic, Google, AWS Bedrock)"
    echo "  llm-multi-provider - LLM API validation and performance comparison"
    echo "  llm-selection     - LLM model selection UI tests"
    echo ""
    echo "🛠️ Tools:"
    echo "  tools              - All tools tests (CRUD + Vibe Coding with all providers)"
    echo "  tools-crud         - Tools CRUD operations tests"
    echo "  vibe-coding        - Vibe coding with multi-provider LLM testing (both platforms)"
    echo "  vibe-coding-mobile - Vibe coding tests on mobile (Pixel 5)"
    echo "  vibe-coding-desktop- Vibe coding tests on desktop (Chrome)"
    echo ""
    echo "🧪 Test Categories:"
    echo "  regression   - Critical regression tests (mock Cognito only)"
    echo "  local        - Run tests in local mode (no AWS Secrets Manager)"
    # echo "  real-cognito - Real Cognito integration tests only (actual AWS)"
    echo ""
    echo "Usage:"
    echo "  just test-e2e                                 # Run all tests (mock + real Cognito)"
    echo "  just test-e2e local                           # Run tests in local mode (no AWS)"
    echo "  just test-e2e <suite>                         # Run specific suite on both platforms"
    echo "  just test-e2e <suite> --platform mobile       # Run suite on mobile only"
    echo "  just test-e2e <suite> --platform desktop      # Run suite on desktop only"
    echo "  just test-e2e-file <file>                     # Run specific test file"
    echo "  just test-e2e-grep <pattern>                  # Run tests matching pattern"
    echo "  just test-e2e list                            # Show this list"
    echo ""
    echo "🖥️ Available Platforms:"
    echo "  mobile, desktop, chrome, chromium"
    echo ""
    echo "Examples:"
    echo "  just test-e2e vibe-coding                      # Run on both platforms"
    echo "  just test-e2e vibe-coding --platform mobile    # Run on mobile only"
    echo "  just test-e2e-file tests/integration/login.spec.ts  # Run specific file"
    echo "  just test-e2e-grep \"login\"                    # Run tests matching 'login'"
    echo ""
    echo "📁 Test Results:"
    echo "  All test results are saved to: test_results/DD-MM-YY-HH-MM-(MOBILE/DESKTOP/BOTH)/"
    echo ""
    echo "Note: 'all' and 'login' suites run both mock and real Cognito tests"
    echo "      Other suites run only mock Cognito tests for fast execution"

# Internal helper: Run E2E suite with mock Cognito
_run-e2e-suite pattern description:
    #!/bin/bash
    set -e
    trap 'just stop-test-servers' EXIT
    echo "🧪 Running {{description}}"

    # Load secrets for E2E tests
    echo "🔐 Loading secrets for E2E tests..."
    just _load-test-secrets

    # Create timestamp-based test results directory
    TIMESTAMP=$(date +"%d-%m-%y-%H-%M")
    TEST_RESULTS_ROOT="test_results"
    mkdir -p "$TEST_RESULTS_ROOT"
    FINAL_RESULTS_DIR="$TEST_RESULTS_ROOT/$TIMESTAMP-BOTH"
    mkdir -p "$FINAL_RESULTS_DIR"

    echo "🗄️ Cleaning test database before starting..."
    # Clean the test database to avoid duplicate entries
    rm -f test_database.db || true
    just start-test-servers
    cd client && PLAYWRIGHT_WORKERS=${PLAYWRIGHT_WORKERS:-1} PLAYWRIGHT_BASE_URL=http://localhost:5889 USE_MEMORY_DB=true npx playwright test --config=playwright.just.config.ts -g "{{pattern}}"
    just stop-test-servers

    # Copy results to timestamped directory
    echo "📁 Copying test results to $FINAL_RESULTS_DIR..."
    cp -r client/test-results/* "$FINAL_RESULTS_DIR/" 2>/dev/null || true

    echo "📊 Test report stored at: $FINAL_RESULTS_DIR/html-report/index.html"
    echo "📁 Test artifacts stored in: $FINAL_RESULTS_DIR/"

# Internal helper: Run E2E suite with mock Cognito and specific platform
_run-e2e-suite-platform pattern description platform:
    #!/bin/bash
    set -e
    trap 'just stop-test-servers' EXIT
    echo "🧪 Running {{description}} on {{platform}}"

    # Load secrets for E2E tests
    echo "🔐 Loading secrets for E2E tests..."
    just _load-test-secrets

    # Create timestamp-based test results directory
    TIMESTAMP=$(date +"%d-%m-%y-%H-%M")
    TEST_RESULTS_ROOT="test_results"
    mkdir -p "$TEST_RESULTS_ROOT"

    # Determine platform suffix
    PLATFORM_SUFFIX=""
    case "{{platform}}" in
        "Mobile Chrome")
            PLATFORM_SUFFIX="MOBILE"
            ;;
        "chromium")
            PLATFORM_SUFFIX="DESKTOP"
            ;;
        *)
            PLATFORM_SUFFIX="{{platform}}"
            ;;
    esac

    FINAL_RESULTS_DIR="$TEST_RESULTS_ROOT/$TIMESTAMP-$PLATFORM_SUFFIX"
    mkdir -p "$FINAL_RESULTS_DIR"

    echo "🗄️ Cleaning test database before starting..."
    # Clean the test database to avoid duplicate entries
    rm -f test_database.db || true
    just start-test-servers
    cd client && PLAYWRIGHT_WORKERS=${PLAYWRIGHT_WORKERS:-1} PLAYWRIGHT_BASE_URL=http://localhost:5889 USE_MEMORY_DB=true npx playwright test --config=playwright.just.config.ts --project="{{platform}}" -g "{{pattern}}"
    just stop-test-servers

    # Copy results to timestamped directory
    echo "📁 Copying test results to $FINAL_RESULTS_DIR..."
    cp -r client/test-results/* "$FINAL_RESULTS_DIR/" 2>/dev/null || true

    echo "📊 Test report stored at: $FINAL_RESULTS_DIR/html-report/index.html"
    echo "📁 Test artifacts stored in: $FINAL_RESULTS_DIR/"

# Generic helper: Run suite with platform logic (both platforms if no platform specified)
_run-suite-with-platform pattern description platform:
    #!/bin/bash
    set -e

    # Create shared timestamp for both platforms
    TIMESTAMP=$(date +"%d-%m-%y-%H-%M")
    TEST_RESULTS_ROOT="test_results"
    mkdir -p "$TEST_RESULTS_ROOT"

    if [[ -n "{{platform}}" ]]; then
        echo "🧪 Running {{description}} on {{platform}}..."
        just _run-e2e-suite-platform-with-timestamp "{{pattern}}" "{{description}}" "{{platform}}" "$TIMESTAMP"
    else
        echo "🧪 Running {{description}} on both platforms..."
        just _run-e2e-suite-platform-with-timestamp "{{pattern}}" "{{description}} (Desktop)" "chromium" "$TIMESTAMP"
        just _run-e2e-suite-platform-with-timestamp "{{pattern}}" "{{description}} (Mobile)" "Mobile Chrome" "$TIMESTAMP"
    fi

# Internal helper: Run E2E suite with mock Cognito and specific platform using provided timestamp
_run-e2e-suite-platform-with-timestamp pattern description platform timestamp:
    #!/bin/bash
    set -e
    trap 'just stop-test-servers' EXIT
    echo "🧪 Running {{description}} on {{platform}}"

    # Load secrets for E2E tests
    echo "🔐 Loading secrets for E2E tests..."
    just _load-test-secrets

    # Use provided timestamp for test results directory
    TEST_RESULTS_ROOT="test_results"
    mkdir -p "$TEST_RESULTS_ROOT"

    # Determine platform suffix
    PLATFORM_SUFFIX=""
    case "{{platform}}" in
        "Mobile Chrome")
            PLATFORM_SUFFIX="MOBILE"
            ;;
        "chromium")
            PLATFORM_SUFFIX="DESKTOP"
            ;;
        *)
            PLATFORM_SUFFIX="{{platform}}"
            ;;
    esac

    FINAL_RESULTS_DIR="$TEST_RESULTS_ROOT/{{timestamp}}-$PLATFORM_SUFFIX"
    mkdir -p "$FINAL_RESULTS_DIR"

    echo "🗄️ Cleaning test database before starting..."
    # Clean the test database to avoid duplicate entries
    rm -f test_database.db || true
    just start-test-servers
    cd client && PLAYWRIGHT_WORKERS=${PLAYWRIGHT_WORKERS:-1} PLAYWRIGHT_BASE_URL=http://localhost:5889 USE_MEMORY_DB=true npx playwright test --config=playwright.just.config.ts --project="{{platform}}" -g "{{pattern}}"
    just stop-test-servers

    # Copy results to timestamped directory
    echo "📁 Copying test results to $FINAL_RESULTS_DIR..."
    cp -r client/test-results/* "$FINAL_RESULTS_DIR/" 2>/dev/null || true

    echo "📊 Test report stored at: $FINAL_RESULTS_DIR/html-report/index.html"
    echo "📁 Test artifacts stored in: $FINAL_RESULTS_DIR/"

# Internal helper: Run E2E suite with real Cognito
_run-e2e-suite-real-cognito pattern description:
    #!/bin/bash
    set -e
    trap 'just stop-test-servers' EXIT
    echo "🧪 Running {{description}}"

    # Load secrets for E2E tests
    echo "🔐 Loading secrets for E2E tests..."
    just _load-test-secrets

    # Create timestamp-based test results directory
    TIMESTAMP=$(date +"%d-%m-%y-%H-%M")
    TEST_RESULTS_ROOT="test_results"
    mkdir -p "$TEST_RESULTS_ROOT"
    FINAL_RESULTS_DIR="$TEST_RESULTS_ROOT/$TIMESTAMP-BOTH"
    mkdir -p "$FINAL_RESULTS_DIR"

    just start-test-servers-real-cognito
    cd client && PLAYWRIGHT_WORKERS=10 PLAYWRIGHT_BASE_URL=http://localhost:5889 npx playwright test --config=playwright.just.config.ts -g "{{pattern}}"
    just stop-test-servers

    # Copy results to timestamped directory
    echo "📁 Copying test results to $FINAL_RESULTS_DIR..."
    cp -r client/test-results/* "$FINAL_RESULTS_DIR/" 2>/dev/null || true

    echo "📊 Test report stored at: $FINAL_RESULTS_DIR/html-report/index.html"
    echo "📁 Test artifacts stored in: $FINAL_RESULTS_DIR/"

# SSH key management commands
ssh-use-germanilia:
    cp /tmp/host-germanilia-key ~/.ssh/id_rsa
    chmod 600 ~/.ssh/id_rsa
    echo "Now using germanilia SSH key"
    ssh-add -l

ssh-use-iliagerman:
    cp /tmp/host-iliagerman-key ~/.ssh/id_rsa
    chmod 600 ~/.ssh/id_rsa
    echo "Now using iliagerman SSH key"
    ssh-add -l

ssh-status:
    echo "Current SSH key fingerprint:"
    ssh-keygen -lf ~/.ssh/id_rsa
    echo "\nLoaded SSH keys:"
    ssh-add -l

git-test-connection:
    ssh -T git@github.com

# Create Cognito User Pool and Client in AWS (only if they don't exist)
create_cognito:
    #!/bin/bash
    set -e

    # Change to backend directory to access configuration files
    cd backend

    # Load environment variables from .env file based on APP_ENV
    APP_ENV=${APP_ENV:-development}
    if [ -f ".env.$APP_ENV" ]; then
        export $(grep -v '^#' .env.$APP_ENV | xargs)
    fi

    # Load AWS credentials from secrets.yaml
    if [ -f "libs/common/secrets.yaml" ]; then
        echo "Loading AWS credentials from libs/common/secrets.yaml..."
        export AWS_ACCESS_KEY_ID=$(python3 -c "import yaml; data=yaml.safe_load(open('libs/common/secrets.yaml')); print(data['aws']['access_key_id'])")
        export AWS_SECRET_ACCESS_KEY=$(python3 -c "import yaml; data=yaml.safe_load(open('libs/common/secrets.yaml')); print(data['aws']['secret_access_key'])")
        export AWS_DEFAULT_REGION=$(python3 -c "import yaml; data=yaml.safe_load(open('libs/common/secrets.yaml')); print(data['aws']['region'])")
        echo "✓ AWS credentials loaded successfully"
    else
        echo "Warning: libs/common/secrets.yaml not found. Make sure AWS credentials are configured."
    fi

    # Use environment variables or defaults
    POOL_NAME=${COGNITO_POOL_NAME:-"MyAppUserPool"}
    CLIENT_NAME=${COGNITO_CLIENT_NAME:-"MyAppClient"}
    REGION=${COGNITO_REGION:-"us-east-1"}

    # Override AWS_DEFAULT_REGION with COGNITO_REGION if specified
    if [ -n "$COGNITO_REGION" ]; then
        export AWS_DEFAULT_REGION="$REGION"
        echo "Using Cognito region: $REGION"
    fi

    echo "Checking if Cognito User Pool exists in AWS..."

    # Try to find existing user pool by name
    EXISTING_POOL=$(aws cognito-idp list-user-pools --max-items 60 --region $REGION --query "UserPools[?Name=='$POOL_NAME'].Id" --output text 2>/dev/null || echo "")

    if [ -n "$EXISTING_POOL" ] && [ "$EXISTING_POOL" != "None" ]; then
        USER_POOL_ID="$EXISTING_POOL"
        echo "✓ User Pool already exists (ID: $USER_POOL_ID)"

        # Check if client exists
        EXISTING_CLIENT=$(aws cognito-idp list-user-pool-clients --user-pool-id "$USER_POOL_ID" --region $REGION --query "UserPoolClients[?ClientName=='$CLIENT_NAME'].ClientId" --output text 2>/dev/null || echo "")

        if [ -n "$EXISTING_CLIENT" ] && [ "$EXISTING_CLIENT" != "None" ]; then
            CLIENT_ID="$EXISTING_CLIENT"
            echo "✓ User Pool Client already exists (ID: $CLIENT_ID)"
            echo "Cognito resources are already set up!"
        else
            echo "User Pool exists but Client is missing. Creating Client..."
            # Create user pool client
            CLIENT_RESPONSE=$(aws cognito-idp create-user-pool-client \
                --user-pool-id "$USER_POOL_ID" \
                --client-name "$CLIENT_NAME" \
                --explicit-auth-flows "ALLOW_USER_PASSWORD_AUTH" "ALLOW_REFRESH_TOKEN_AUTH" "ALLOW_USER_SRP_AUTH" \
                --region $REGION \
                --query "UserPoolClient.ClientId" \
                --output text)
            CLIENT_ID="$CLIENT_RESPONSE"
            echo "✓ User Pool Client created successfully!"
        fi
    else
        echo "User Pool doesn't exist. Creating User Pool and Client..."

        # Create user pool with environment-specific configuration
        if [ "$APP_ENV" = "development" ]; then
            # Development: Simple setup, no email verification required
            echo "Creating development User Pool (no email verification)..."
            USER_POOL_RESPONSE=$(aws cognito-idp create-user-pool \
                --pool-name "$POOL_NAME" \
                --region $REGION \
                --policies '{"PasswordPolicy":{"MinimumLength":8,"RequireUppercase":false,"RequireLowercase":false,"RequireNumbers":false,"RequireSymbols":false}}' \
                --username-attributes email \
                --admin-create-user-config '{"AllowAdminCreateUserOnly":false}' \
                --query "UserPool.Id" \
                --output text)
        else
            # Production: Require email verification
            echo "Creating production User Pool (with email verification)..."
            USER_POOL_RESPONSE=$(aws cognito-idp create-user-pool \
                --pool-name "$POOL_NAME" \
                --region $REGION \
                --policies '{"PasswordPolicy":{"MinimumLength":8,"RequireUppercase":true,"RequireLowercase":true,"RequireNumbers":true,"RequireSymbols":false}}' \
                --username-attributes email \
                --admin-create-user-config '{"AllowAdminCreateUserOnly":false}' \
                --auto-verified-attributes email \
                --verification-message-template '{"DefaultEmailOption":"CONFIRM_WITH_CODE","EmailMessage":"Your verification code is {####}","EmailSubject":"Your verification code"}' \
                --query "UserPool.Id" \
                --output text)
        fi

        USER_POOL_ID="$USER_POOL_RESPONSE"
        echo "✓ User Pool created successfully! (ID: $USER_POOL_ID)"

        # Create user pool client
        CLIENT_RESPONSE=$(aws cognito-idp create-user-pool-client \
            --user-pool-id "$USER_POOL_ID" \
            --client-name "$CLIENT_NAME" \
            --explicit-auth-flows "ALLOW_USER_PASSWORD_AUTH" "ALLOW_REFRESH_TOKEN_AUTH" "ALLOW_USER_SRP_AUTH" \
            --region $REGION \
            --query "UserPoolClient.ClientId" \
            --output text)

        CLIENT_ID="$CLIENT_RESPONSE"
        echo "✓ User Pool Client created successfully!"
    fi

    echo ""
    echo "🎉 Cognito setup complete for environment: $APP_ENV"
    echo "User Pool Name: $POOL_NAME"
    echo "User Pool ID: $USER_POOL_ID"
    echo "Client Name: $CLIENT_NAME"
    echo "Client ID: $CLIENT_ID"
    echo "Region: $REGION"
    echo ""
    echo "💡 Note: This User Pool has minimal password requirements and no email verification for development ease."
    echo ""

    # Automatically add Cognito IDs to environment file
    echo "📝 Updating .env.$APP_ENV file..."
    if [ -f ".env.$APP_ENV" ]; then
        # Create a backup
        cp ".env.$APP_ENV" ".env.$APP_ENV.backup"

        # Remove any existing Cognito ID lines first (but keep COGNITO_REGION)
        grep -v "^COGNITO_USER_POOL_ID=" ".env.$APP_ENV" | grep -v "^COGNITO_CLIENT_ID=" | grep -v "^# Cognito IDs (from create_cognito" > ".env.$APP_ENV.tmp"
        mv ".env.$APP_ENV.tmp" ".env.$APP_ENV"

        # Add the new Cognito IDs
        echo "# Cognito IDs (from create_cognito_$APP_ENV output)" >> ".env.$APP_ENV"
        echo "COGNITO_USER_POOL_ID=$USER_POOL_ID" >> ".env.$APP_ENV"
        echo "COGNITO_CLIENT_ID=$CLIENT_ID" >> ".env.$APP_ENV"

        echo "✓ Added Cognito configuration to .env.$APP_ENV"
        echo "✓ Backup saved as .env.$APP_ENV.backup"
    else
        echo "⚠️  .env.$APP_ENV file not found. Please create it and add:"
        echo "COGNITO_USER_POOL_ID=$USER_POOL_ID"
        echo "COGNITO_CLIENT_ID=$CLIENT_ID"
        echo "COGNITO_REGION=$REGION"
    fi

    echo ""
    echo "🎉 Cognito setup complete! Your backend will automatically use the new configuration."

# Create Cognito for development environment
create_cognito_dev:
    APP_ENV=development just create_cognito

# Create Cognito for production environment
create_cognito_prod:
    APP_ENV=production just create_cognito

# Delete Cognito User Pool and Client
delete_cognito:
    #!/bin/bash
    set -e
    cd backend

    # Load environment variables
    APP_ENV=${APP_ENV:-development}
    if [ -f ".env.$APP_ENV" ]; then
        export $(grep -v '^#' .env.$APP_ENV | xargs)
    fi

    # Load AWS credentials from secrets.yaml
    if [ -f "libs/common/secrets.yaml" ]; then
        echo "Loading AWS credentials from libs/common/secrets.yaml..."
        export AWS_ACCESS_KEY_ID=$(python3 -c "import yaml; data=yaml.safe_load(open('libs/common/secrets.yaml')); print(data['aws']['access_key_id'])")
        export AWS_SECRET_ACCESS_KEY=$(python3 -c "import yaml; data=yaml.safe_load(open('libs/common/secrets.yaml')); print(data['aws']['secret_access_key'])")
        export AWS_DEFAULT_REGION=$(python3 -c "import yaml; data=yaml.safe_load(open('libs/common/secrets.yaml')); print(data['aws']['region'])")
        echo "AWS credentials loaded successfully"
    fi

    # Get Cognito config from environment variables (not secrets.yaml)
    USER_POOL_ID=${COGNITO_USER_POOL_ID:-""}
    CLIENT_ID=${COGNITO_CLIENT_ID:-""}
    REGION=${COGNITO_REGION:-"us-east-1"}

    if [ -z "$USER_POOL_ID" ]; then
        echo "ERROR: COGNITO_USER_POOL_ID not found in environment variables"
        echo "Make sure .env.$APP_ENV contains COGNITO_USER_POOL_ID"
        exit 1
    fi

    echo "Deleting Cognito resources for environment: $APP_ENV"
    echo "User Pool ID: $USER_POOL_ID"
    echo "Client ID: $CLIENT_ID"
    echo "Region: $REGION"

    # Delete client if specified
    if [ -n "$CLIENT_ID" ]; then
        echo "Deleting User Pool Client: $CLIENT_ID"
        aws cognito-idp delete-user-pool-client --user-pool-id "$USER_POOL_ID" --client-id "$CLIENT_ID" --region "$REGION" || echo "Client deletion failed or already deleted"
    fi

    # Delete the user pool
    echo "Deleting User Pool: $USER_POOL_ID"
    aws cognito-idp delete-user-pool --user-pool-id "$USER_POOL_ID" --region "$REGION"

    # Remove Cognito IDs from environment file
    echo "Cleaning up environment variables..."
    if [ -f ".env.$APP_ENV" ]; then
        # Create a backup
        cp ".env.$APP_ENV" ".env.$APP_ENV.backup"

        # Remove the Cognito ID lines and related comments
        grep -v "^COGNITO_USER_POOL_ID=" ".env.$APP_ENV" | grep -v "^COGNITO_CLIENT_ID=" | grep -v "^# Cognito IDs (from create_cognito" > ".env.$APP_ENV.tmp"
        mv ".env.$APP_ENV.tmp" ".env.$APP_ENV"

        echo "Removed COGNITO_USER_POOL_ID and COGNITO_CLIENT_ID from .env.$APP_ENV"
        echo "Backup saved as .env.$APP_ENV.backup"
    fi

    echo "Cognito resources deleted successfully"

# Delete Cognito for development environment
delete_cognito_dev:
    APP_ENV=development just delete_cognito

# Delete Cognito for production environment
delete_cognito_prod:
    APP_ENV=production just delete_cognito

# Create Cognito for hackathon environment
create_cognito_hackathon:
    APP_ENV=hackathon just create_cognito

# Delete Cognito for hackathon environment
delete_cognito_hackathon:
    APP_ENV=hackathon just delete_cognito

# Setup AWS services (LocalStack SQS + Real AWS Cognito)
setup_aws_services:
    just create_sqs
    just create_cognito

# Generate migration for Cognito fields
generate_cognito_migration:
    cd backend && python -m app.db.generate_cognito_migration

# ============================================================================
# HACKATHON ENVIRONMENT COMMANDS
# ============================================================================

# Create AWS Secrets Manager secret for hackathon environment
create_hackathon_secret:
    #!/bin/bash
    set -e
    echo "🔐 Creating hackathon_secret in AWS Secrets Manager..."
    chmod +x scripts/create-hackathon-secret.sh
    ./scripts/create-hackathon-secret.sh

# Deploy frontend to S3 and invalidate CloudFront for hackathon
deploy_hackathon_frontend:
    #!/bin/bash
    set -e
    echo "🚀 Deploying frontend to S3 for hackathon environment..."
    chmod +x scripts/deploy-frontend-s3.sh
    ./scripts/deploy-frontend-s3.sh hackathon

# Invalidate CloudFront cache for hackathon environment
invalidate_hackathon_cloudfront paths="/*":
    #!/bin/bash
    set -e
    echo "🔄 Invalidating CloudFront cache for hackathon..."
    chmod +x scripts/invalidate-cloudfront.sh
    ./scripts/invalidate-cloudfront.sh hackathon "{{paths}}"

# Update ECS backend service for hackathon environment
update_hackathon_backend:
    #!/bin/bash
    set -e
    echo "🚀 Updating ECS backend service for hackathon..."
    aws ecs update-service \
        --cluster agentleague-hackathon-cluster \
        --service agentleague-hackathon-backend \
        --force-new-deployment \
        --region us-east-1
    echo "✅ ECS backend service update initiated"
    echo "⏳ Waiting for service to stabilize..."
    aws ecs wait services-stable \
        --cluster agentleague-hackathon-cluster \
        --services agentleague-hackathon-backend \
        --region us-east-1
    echo "✅ ECS service is stable"

# Full deployment for hackathon environment (frontend + backend)
deploy_hackathon: deploy_hackathon_frontend update_hackathon_backend
    @echo "🎉 Hackathon deployment complete!"
    @echo "Frontend: https://app.hackathon.agentleague.ai"
    @echo "Backend: https://api.hackathon.agentleague.ai"

# Export AWS environment variables from secrets.yaml to current terminal session
aws:
    #!/bin/bash
    set -e

    # Check if secrets.yaml exists
    if [ ! -f "libs/common/secrets.yaml" ]; then
        echo "ERROR: libs/common/secrets.yaml not found" >&2
        echo "Please ensure the secrets file exists with AWS credentials" >&2
        exit 1
    fi

    # Extract AWS credentials using Python
    AWS_ACCESS_KEY_ID=$(python3 -c "import yaml; data=yaml.safe_load(open('libs/common/secrets.yaml')); print(data['opencode']['access_key_id'])" 2>/dev/null || echo "")
    AWS_SECRET_ACCESS_KEY=$(python3 -c "import yaml; data=yaml.safe_load(open('libs/common/secrets.yaml')); print(data['opencode']['secret_access_key'])" 2>/dev/null || echo "")
    AWS_DEFAULT_REGION=$(python3 -c "import yaml; data=yaml.safe_load(open('libs/common/secrets.yaml')); print(data['opencode']['region'])" 2>/dev/null || echo "")

    # Check if credentials were loaded successfully
    if [ -z "$AWS_ACCESS_KEY_ID" ] || [ -z "$AWS_SECRET_ACCESS_KEY" ] || [ -z "$AWS_DEFAULT_REGION" ]; then
        echo "ERROR: Failed to load AWS credentials from secrets.yaml" >&2
        echo "Please ensure the file contains valid opencode.access_key_id, opencode.secret_access_key, and opencode.region" >&2
        exit 1
    fi

    # Output export statements that can be evaluated
    echo "export AWS_ACCESS_KEY_ID=\"$AWS_ACCESS_KEY_ID\""
    echo "export AWS_SECRET_ACCESS_KEY=\"$AWS_SECRET_ACCESS_KEY\""
    echo "export AWS_DEFAULT_REGION=\"$AWS_DEFAULT_REGION\""

    # Output informational messages to stderr so they don't interfere with eval
    echo "# ✓ AWS credentials loaded from libs/common/secrets.yaml" >&2
    echo "#   AWS_ACCESS_KEY_ID: ${AWS_ACCESS_KEY_ID:0:8}..." >&2
    echo "#   AWS_SECRET_ACCESS_KEY: ${AWS_SECRET_ACCESS_KEY:0:8}..." >&2
    echo "#   AWS_DEFAULT_REGION: $AWS_DEFAULT_REGION" >&2
    echo "#" >&2
    echo "# To set these variables in your current shell, run:" >&2
    echo "#   eval \"\$(just aws)\"" >&2

# Internal helper: Load secrets for E2E tests (local secrets.yaml or AWS Secrets Manager)
# Note: AWS credentials now use the default AWS credential chain (env vars, profile, IAM role)
# Local secrets.yaml contains LLM provider API keys and other application secrets
_load-test-secrets:
    #!/bin/bash
    set -e

    # Check if local secrets.yaml exists
    if [ -f "libs/common/secrets.yaml" ]; then
        echo "✅ Found local secrets.yaml - using local secrets for E2E tests"

        # Verify the secrets file is valid YAML
        if python3 -c "import yaml; yaml.safe_load(open('libs/common/secrets.yaml'))" 2>/dev/null; then
            echo "✅ Local secrets.yaml is valid"
        else
            echo "❌ Local secrets.yaml is invalid YAML format"
            exit 1
        fi

        echo "ℹ️  Using default AWS credential chain (env vars, profile, or IAM role)"
        exit 0
    fi

    # No local secrets found, try AWS Secrets Manager
    echo "⚠️  No local secrets.yaml found - attempting to load from AWS Secrets Manager..."

    # Check if AWS CLI is available
    if ! command -v aws &> /dev/null; then
        echo "❌ AWS CLI not found and no local secrets.yaml available"
        echo "💡 Please either:"
        echo "   1. Install AWS CLI and configure credentials, or"
        echo "   2. Create libs/common/secrets.yaml with your secrets"
        echo "   3. Copy libs/common/secrets.example.yaml to libs/common/secrets.yaml and fill in values"
        exit 1
    fi

    # Determine environment and secret name
    APP_ENV=${APP_ENV:-test}
    if [ "$APP_ENV" = "production" ]; then
        SECRET_NAME="prod_secret"
    elif [ "$APP_ENV" = "development" ]; then
        SECRET_NAME="dev_secret"
    else
        SECRET_NAME="${APP_ENV}_secret"
    fi

    # Try to get AWS region from environment or use default
    AWS_REGION=${AWS_DEFAULT_REGION:-us-east-1}

    echo "🔍 Attempting to load secret '$SECRET_NAME' from AWS Secrets Manager (region: $AWS_REGION)..."

    # Try to retrieve the secret
    if aws secretsmanager get-secret-value --secret-id "$SECRET_NAME" --region "$AWS_REGION" --query 'SecretString' --output text > /tmp/aws_secrets.yaml 2>/dev/null; then
        echo "✅ Successfully retrieved secrets from AWS Secrets Manager"

        # Verify the retrieved secret is valid YAML
        if python3 -c "import yaml; yaml.safe_load(open('/tmp/aws_secrets.yaml'))" 2>/dev/null; then
            echo "✅ AWS secrets are valid YAML format"

            # Copy to the expected location for the application to use
            cp /tmp/aws_secrets.yaml libs/common/secrets.yaml
            echo "✅ AWS secrets copied to libs/common/secrets.yaml for E2E tests"

            # Clean up temporary file
            rm -f /tmp/aws_secrets.yaml
        else
            echo "❌ Retrieved AWS secret is not valid YAML format"
            rm -f /tmp/aws_secrets.yaml
            exit 1
        fi
    else
        echo "❌ Failed to retrieve secrets from AWS Secrets Manager"
        echo "💡 Please either:"
        echo "   1. Ensure AWS credentials are configured (aws configure)"
        echo "   2. Verify the secret '$SECRET_NAME' exists in region '$AWS_REGION'"
        echo "   3. Create libs/common/secrets.yaml with your local secrets"
        echo "   4. Copy libs/common/secrets.example.yaml to libs/common/secrets.yaml and fill in values"
        exit 1
    fi

    echo "✅ Secrets loaded successfully for E2E tests"