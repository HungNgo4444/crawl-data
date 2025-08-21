#!/bin/bash

# Migration Script: migrate.sh (Deployment version)
# Description: Database migration runner for deployment environment
# Date: 2025-08-11

set -e  # Exit on any error

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
MIGRATIONS_DIR="${SCRIPT_DIR}/migrations"
LOG_FILE="${SCRIPT_DIR}/migration.log"

# Load environment from .env file
if [ -f "${SCRIPT_DIR}/.env" ]; then
    export $(grep -v '^#' "${SCRIPT_DIR}/.env" | xargs)
fi

# Database connection parameters (use environment variables)
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-crawler_db}"
DB_USER="${DB_USER:-crawler_user}"
DB_PASSWORD="${DB_PASSWORD:-}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${1}" | tee -a "${LOG_FILE}"
}

# Error handling
error_exit() {
    log "${RED}ERROR: ${1}${NC}"
    exit 1
}

# Success message
success() {
    log "${GREEN}SUCCESS: ${1}${NC}"
}

# Warning message
warning() {
    log "${YELLOW}WARNING: ${1}${NC}"
}

# Check if psql is available
check_prerequisites() {
    # Try psql from docker container first
    if docker-compose ps postgres | grep -q "Up"; then
        log "Using PostgreSQL from Docker container"
        PSQL_CMD="docker-compose exec -T postgres psql"
        return 0
    fi
    
    # Try local psql
    if command -v psql &> /dev/null; then
        PSQL_CMD="psql"
        return 0
    fi
    
    error_exit "PostgreSQL not available. Start Docker containers or install psql client tools."
}

# Test database connection
test_connection() {
    log "Testing database connection..."
    
    if [ "$PSQL_CMD" = "docker-compose exec -T postgres psql" ]; then
        docker-compose exec -T postgres psql -U "${DB_USER}" -d "${DB_NAME}" -c "SELECT 1;" > /dev/null 2>&1
    else
        PGPASSWORD="${DB_PASSWORD}" psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" -c "SELECT 1;" > /dev/null 2>&1
    fi
    
    if [ $? -eq 0 ]; then
        success "Database connection successful"
    else
        error_exit "Cannot connect to database. Check connection parameters and Docker containers."
    fi
}

# Execute SQL file with error handling
execute_sql_file() {
    local sql_file="$1"
    local operation="$2"
    
    log "Executing ${operation}: $(basename "${sql_file}")"
    
    if [ "$PSQL_CMD" = "docker-compose exec -T postgres psql" ]; then
        # Use stdin to execute SQL from file
        docker-compose exec -T postgres psql -U "${DB_USER}" -d "${DB_NAME}" < "${sql_file}" 2>&1 | tee -a "${LOG_FILE}"
    else
        PGPASSWORD="${DB_PASSWORD}" psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" -f "${sql_file}" 2>&1 | tee -a "${LOG_FILE}"
    fi
    
    if [ ${PIPESTATUS[0]} -eq 0 ]; then
        success "Successfully executed $(basename "${sql_file}")"
        return 0
    else
        error_exit "Failed to execute $(basename "${sql_file}")"
        return 1
    fi
}

# Forward migration
migrate_up() {
    log "Starting forward migration..."
    
    # Execute migrations in order
    for migration_file in "${MIGRATIONS_DIR}"/*.sql; do
        if [ -f "${migration_file}" ]; then
            execute_sql_file "${migration_file}" "migration"
        fi
    done
    
    success "All migrations completed successfully"
}

# Check migration status
migration_status() {
    log "Checking migration status..."
    
    if [ "$PSQL_CMD" = "docker-compose exec -T postgres psql" ]; then
        docker-compose exec -T postgres psql -U "${DB_USER}" -d "${DB_NAME}" -c "
        SELECT version, applied_at, description 
        FROM schema_migrations 
        ORDER BY applied_at;" 2>/dev/null || warning "schema_migrations table not found - no migrations applied yet"
    else
        PGPASSWORD="${DB_PASSWORD}" psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" -c "
        SELECT version, applied_at, description 
        FROM schema_migrations 
        ORDER BY applied_at;" 2>/dev/null || warning "schema_migrations table not found - no migrations applied yet"
    fi
}

# Show help
show_help() {
    echo "Database Migration Tool (Deployment Version)"
    echo ""
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo "  up      - Run forward migrations (default)"
    echo "  status  - Show migration status"
    echo "  test    - Test database connection"
    echo "  help    - Show this help"
    echo ""
    echo "Environment Variables (loaded from .env):"
    echo "  DB_HOST     - Database host (default: localhost)"
    echo "  DB_PORT     - Database port (default: 5432)"
    echo "  DB_NAME     - Database name (default: crawler_db)"
    echo "  DB_USER     - Database user (default: crawler_user)"
    echo "  DB_PASSWORD - Database password"
}

# Main execution
main() {
    log "=== Database Migration Tool Started at $(date) ==="
    
    # Check prerequisites
    check_prerequisites
    
    # Parse command
    case "${1:-up}" in
        "up")
            test_connection
            migrate_up
            ;;
        "status")
            test_connection
            migration_status
            ;;
        "test")
            test_connection
            ;;
        "help"|"-h"|"--help")
            show_help
            ;;
        *)
            error_exit "Unknown command: $1. Use 'help' to see available commands."
            ;;
    esac
    
    log "=== Migration tool completed at $(date) ==="
}

# Run main function with all arguments
main "$@"