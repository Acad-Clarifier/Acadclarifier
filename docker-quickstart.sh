#!/bin/bash
# AcadClarifier Docker Quick Start Script
# Usage: bash ./docker-quickstart.sh [up|down|logs|build|clean]

set -e

PROJECT_NAME="acadclarifier"
COMPOSE_FILE="docker-compose.yml"
ENV_FILE=".env"
ENV_EXAMPLE=".env.example"

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo_header() {
    echo -e "${GREEN}=== $1 ===${NC}"
}

echo_error() {
    echo -e "${RED}ERROR: $1${NC}"
}

echo_warning() {
    echo -e "${YELLOW}WARNING: $1${NC}"
}

echo_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

# Check prerequisites
check_prereqs() {
    echo_header "Checking Prerequisites"
    
    if ! command -v docker &> /dev/null; then
        echo_error "Docker not found. Install from https://docs.docker.com/get-docker/"
        exit 1
    fi
    echo_success "Docker installed: $(docker --version)"
    
    if ! command -v docker-compose &> /dev/null; then
        echo_error "Docker Compose not found. Install from https://docs.docker.com/compose/install/"
        exit 1
    fi
    echo_success "Docker Compose installed: $(docker compose version)"
}

# Create .env file if missing
setup_env() {
    if [ ! -f "$ENV_FILE" ]; then
        if [ ! -f "$ENV_EXAMPLE" ]; then
            echo_error ".env.example not found!"
            exit 1
        fi
        
        echo_warning ".env not found. Creating from .env.example..."
        cp "$ENV_EXAMPLE" "$ENV_FILE"
        echo_warning "IMPORTANT: Edit .env with your configuration, especially DB_PASSWORD!"
        echo_warning "Then run: bash docker-quickstart.sh up"
        exit 0
    fi
    echo_success ".env file exists"
}

# Build image
build_image() {
    echo_header "Building Docker Image"
    docker compose -f "$COMPOSE_FILE" build
    echo_success "Image built successfully"
}

# Start services
start_services() {
    echo_header "Starting Services"
    docker compose -f "$COMPOSE_FILE" up -d
    
    echo_warning "Waiting for services to be healthy..."
    sleep 15
    
    # Check status
    docker compose -f "$COMPOSE_FILE" ps
    
    echo ""
    echo_success "Services started!"
    echo ""
    echo_header "Access Your Application"
    echo "  Backend API: http://localhost:5000"
    echo "  Frontend:   http://localhost:8501 (if configured)"
    echo "  Database:   localhost:5432"
    echo ""
    echo "View logs: bash docker-quickstart.sh logs"
    echo "Stop services: bash docker-quickstart.sh down"
}

# Initialize database
init_database() {
    echo_header "Initializing Database"
    
    echo "Running migrations..."
    docker compose -f "$COMPOSE_FILE" exec -T backend flask db upgrade || true
    
    echo_success "Database initialized"
}

# Stop services
stop_services() {
    echo_header "Stopping Services"
    docker compose -f "$COMPOSE_FILE" down
    echo_success "Services stopped"
}

# Show logs
show_logs() {
    docker compose -f "$COMPOSE_FILE" logs --tail 100 -f
}

# Clean everything
clean_all() {
    echo_header "Cleaning Up (WARNING: This removes all data!)"
    echo_warning "Press Ctrl+C within 5 seconds to cancel..."
    sleep 5
    
    docker compose -f "$COMPOSE_FILE" down -v
    echo_success "Cleaned up all services and volumes"
}

# Health check
health_check() {
    echo_header "Health Check"
    
    echo "Checking Docker..."
    docker compose -f "$COMPOSE_FILE" ps
    
    echo ""
    echo "Checking backend health..."
    if curl -s http://localhost:5000/health > /dev/null 2>&1; then
        echo_success "Backend is healthy"
    else
        echo_warning "Backend is not responding on :5000"
    fi
}

# Main command handling
COMMAND="${1:-up}"

case "$COMMAND" in
    up)
        check_prereqs
        setup_env
        build_image
        start_services
        init_database
        health_check
        ;;
    down)
        stop_services
        ;;
    logs)
        show_logs
        ;;
    build)
        check_prereqs
        build_image
        ;;
    clean)
        clean_all
        ;;
    health)
        health_check
        ;;
    status)
        docker compose -f "$COMPOSE_FILE" ps
        ;;
    *)
        echo "Usage: bash docker-quickstart.sh [command]"
        echo ""
        echo "Commands:"
        echo "  up       - Start all services (default)"
        echo "  down     - Stop all services"
        echo "  logs     - View real-time logs"
        echo "  build    - Build Docker image only"
        echo "  clean    - Stop and remove all data (WARNING!)"
        echo "  health   - Run health checks"
        echo "  status   - Show service status"
        ;;
esac
