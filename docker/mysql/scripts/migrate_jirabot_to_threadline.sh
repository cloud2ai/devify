#!/bin/bash

# MariaDB Migration Script: jirabot to threadline
# =============================================
#
# IMPORTANT: This script is SPECIFICALLY designed for migrating from 'jirabot'
# to 'threadline' in this Django project. It is NOT a generic migration tool.
#
# Background: The original name 'jirabot' was too restrictive and couldn't
# encompass all the application's functionality. The app has evolved beyond
# just Jira integration to become a comprehensive threadline management platform.
#
# This script addresses the project renaming issue caused by the original name
# being unable to carry the full scope of features.
#
# DO NOT attempt to use this script for other Django app renamings.
# =============================================

set -e  # Exit immediately if a command exits with a non-zero status

# Get configuration from environment variables, use defaults if not set
DB_HOST="${MYSQL_HOST:-localhost}"
DB_PORT="${MYSQL_PORT:-3306}"
DB_NAME="${MYSQL_DATABASE:-devify}"
DB_USER="${MYSQL_USER:-root}"
DB_PASS="${MYSQL_PASSWORD:-}"
MARIADB_OPTS="${MARIADB_OPTS:---default-character-set=utf8mb4}"

# Color output
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

# Check required environment variables
check_environment() {
    if [ -z "$DB_USER" ]; then
        log_error "MYSQL_USER environment variable not set"
        exit 1
    fi

    if [ -z "$DB_PASS" ]; then
        log_warning "MYSQL_PASSWORD environment variable not set, will connect without password"
    fi

    log_info "Database configuration:"
    log_info "  Host: $DB_HOST (from MYSQL_HOST)"
    log_info "  Port: $DB_PORT (from MYSQL_PORT)"
    log_info "  Database: $DB_NAME (from MYSQL_DATABASE)"
    log_info "  User: $DB_USER (from MYSQL_USER)"
}

# Check MariaDB client
check_mariadb_client() {
    if ! command -v mariadb &> /dev/null; then
        log_error "MariaDB client not installed, please install mariadb-client first"
        exit 1
    fi
}

# Test database connection
test_connection() {
    log_info "Testing database connection..."

    # Build MariaDB connection strings
    if [ -n "$DB_PASS" ]; then
        MARIADB_CMD="mariadb -h$DB_HOST -P$DB_PORT -u$DB_USER -p$DB_PASS $MARIADB_OPTS"
    else
        MARIADB_CMD="mariadb -h$DB_HOST -P$DB_PORT -u$DB_USER $MARIADB_OPTS"
    fi

    if $MARIADB_CMD -e "SELECT 1;" "$DB_NAME" &>/dev/null; then
        log_success "Database connection successful"
    else
        log_error "Database connection failed, please check configuration"
        exit 1
    fi
}

# Check current status
check_current_state() {
    log_info "Checking current database status..."

    # Check jirabot tables
    JIRABOT_TABLES=$($MARIADB_CMD -s -e "
        SELECT table_name FROM information_schema.tables
        WHERE table_schema = '$DB_NAME' AND table_name LIKE 'jirabot_%'
        ORDER BY table_name
    " "$DB_NAME" 2>/dev/null || echo "")

    # Check threadline tables
    THREADLINE_TABLES=$($MARIADB_CMD -s -e "
        SELECT table_name FROM information_schema.tables
        WHERE table_schema = '$DB_NAME' AND table_name LIKE 'threadline_%'
        ORDER BY table_name
    " "$DB_NAME" 2>/dev/null || echo "")

    if [ -n "$JIRABOT_TABLES" ]; then
        log_info "Found jirabot tables:"
        echo "$JIRABOT_TABLES" | while read table; do
            if [ -n "$table" ]; then
                count=$($MARIADB_CMD -s -e "SELECT COUNT(*) FROM \`$table\`" "$DB_NAME" 2>/dev/null || echo "0")
                log_info "  - $table ($count records)"
            fi
        done
    else
        log_warning "No jirabot tables found"
    fi

    if [ -n "$THREADLINE_TABLES" ]; then
        log_info "Found threadline tables:"
        echo "$THREADLINE_TABLES" | while read table; do
            if [ -n "$table" ]; then
                count=$($MARIADB_CMD -s -e "SELECT COUNT(*) FROM \`$table\`" "$DB_NAME" 2>/dev/null || echo "0")
                log_info "  - $table ($count records)"
            fi
        done
    else
        log_info "No threadline tables found"
    fi
}

# Create threadline tables by copying jirabot structure
create_threadline_tables() {
    log_info "Creating threadline table structure..."

    # Get jirabot tables
    JIRABOT_TABLES=$($MARIADB_CMD -s -e "
        SELECT table_name FROM information_schema.tables
        WHERE table_schema = '$DB_NAME' AND table_name LIKE 'jirabot_%'
        ORDER BY table_name
    " "$DB_NAME" 2>/dev/null || echo "")

    if [ -z "$JIRABOT_TABLES" ]; then
        log_error "No jirabot tables found to copy structure from"
        exit 1
    fi

    # Create threadline tables with same structure
    echo "$JIRABOT_TABLES" | while read table; do
        if [ -n "$table" ]; then
            new_table=$(echo "$table" | sed 's/jirabot_/threadline_/')
            log_info "Creating table: $new_table from $table"

            # Check if table already exists
            if $MARIADB_CMD -s -e "SELECT 1 FROM \`$new_table\` LIMIT 1" "$DB_NAME" &>/dev/null; then
                log_info "Table $new_table already exists, skipping creation"
            else
                # Create table with same structure
                if $MARIADB_CMD -e "CREATE TABLE \`$new_table\` LIKE \`$table\`" "$DB_NAME"; then
                    log_success "Table $new_table created successfully"
                else
                    log_error "Failed to create table $new_table"
                    exit 1
                fi
            fi
        fi
    done
}

# Migrate data directly using INSERT ... SELECT
migrate_data() {
    log_info "Migrating data from jirabot to threadline tables..."

    # Define migration order to handle foreign key constraints
    # Tables without dependencies first, then dependent tables
    MIGRATION_ORDER=(
        "jirabot_settings"
        "jirabot_emailtask"
        "jirabot_emailmessage"
        "jirabot_emailattachment"
        "jirabot_jiraissue"
    )

    # Migrate tables in correct order
    for table in "${MIGRATION_ORDER[@]}"; do
        # Check if source table exists
        if $MARIADB_CMD -s -e "SELECT 1 FROM \`$table\` LIMIT 1" "$DB_NAME" &>/dev/null; then
            new_table=$(echo "$table" | sed 's/jirabot_/threadline_/')
            log_info "Migrating data: $table → $new_table"

            # Get record count before migration
            old_count=$($MARIADB_CMD -s -e "SELECT COUNT(*) FROM \`$table\`" "$DB_NAME" 2>/dev/null || echo "0")

                                    # Clear target table before migration to avoid duplicate key errors
            log_info "Clearing target table $new_table before migration..."

            # Use TRUNCATE with foreign key checks disabled (more reliable)
            if $MARIADB_CMD -e "SET FOREIGN_KEY_CHECKS = 0; TRUNCATE TABLE \`$new_table\`; SET FOREIGN_KEY_CHECKS = 1;" "$DB_NAME"; then
                log_success "Table $new_table cleared successfully with TRUNCATE"
            else
                log_warning "TRUNCATE failed, trying alternative method..."

                # Alternative: Delete in smaller batches to avoid foreign key issues
                total_count=$($MARIADB_CMD -s -e "SELECT COUNT(*) FROM \`$new_table\`" "$DB_NAME" 2>/dev/null || echo "0")
                if [ "$total_count" -gt 0 ]; then
                    log_info "Attempting to clear table $new_table in batches..."

                    # Delete in batches of 1000
                    while [ "$total_count" -gt 0 ]; do
                        deleted=$($MARIADB_CMD -s -e "DELETE FROM \`$new_table\` LIMIT 1000" "$DB_NAME" 2>/dev/null || echo "0")
                        if [ "$deleted" -eq 0 ]; then
                            break
                        fi
                        total_count=$($MARIADB_CMD -s -e "SELECT COUNT(*) FROM \`$new_table\`" "$DB_NAME" 2>/dev/null || echo "0")
                        log_info "Deleted batch, remaining: $total_count records"
                    done

                    if [ "$total_count" -eq 0 ]; then
                        log_success "Table $new_table cleared successfully with batch deletion"
                    else
                        log_error "Failed to clear table $new_table completely"
                        exit 1
                    fi
                fi
            fi

            # Verify table is empty
            remaining_count=$($MARIADB_CMD -s -e "SELECT COUNT(*) FROM \`$new_table\`" "$DB_NAME" 2>/dev/null || echo "0")
            if [ "$remaining_count" != "0" ]; then
                log_error "Table $new_table still has $remaining_count records after clearing"
                exit 1
            fi

            # Insert data
            if $MARIADB_CMD -e "INSERT INTO \`$new_table\` SELECT * FROM \`$table\`" "$DB_NAME"; then
                # Verify record count after migration
                new_count=$($MARIADB_CMD -s -e "SELECT COUNT(*) FROM \`$new_table\`" "$DB_NAME" 2>/dev/null || echo "0")
                log_success "Migration successful: $table → $new_table ($old_count → $new_count records)"
            else
                log_error "Migration failed: $table → $new_table"
                exit 1
            fi
        else
            log_warning "Source table $table not found, skipping"
        fi
    done
}

# Update Django migration history
update_migration_history() {
    log_info "Updating Django migration history..."

    if $MARIADB_CMD -e "
        UPDATE django_migrations SET app = 'threadline' WHERE app = 'jirabot'
    " "$DB_NAME"; then
        log_success "Migration history updated successfully"
    else
        log_warning "Migration history update failed (may not have relevant records)"
    fi
}

# Drop original jirabot tables (optional)
drop_jirabot_tables() {
    log_info "Dropping original jirabot tables..."

    JIRABOT_TABLES=$($MARIADB_CMD -s -e "
        SELECT table_name FROM information_schema.tables
        WHERE table_schema = '$DB_NAME' AND table_name LIKE 'jirabot_%'
        ORDER BY table_name
    " "$DB_NAME" 2>/dev/null || echo "")

    if [ -z "$JIRABOT_TABLES" ]; then
        log_info "No jirabot tables to drop"
        return
    fi

    echo "$JIRABOT_TABLES" | while read table; do
        if [ -n "$table" ]; then
            log_info "Dropping table: $table"
            if $MARIADB_CMD -e "DROP TABLE \`$table\`" "$DB_NAME"; then
                log_success "Drop successful: $table"
            else
                log_error "Drop failed: $table"
                exit 1
            fi
        fi
    done
}

# Verify migration results
verify_migration() {
    log_info "Verifying migration results..."

    THREADLINE_TABLES=$($MARIADB_CMD -s -e "
        SELECT table_name FROM information_schema.tables
        WHERE table_schema = '$DB_NAME' AND table_name LIKE 'threadline_%'
        ORDER BY table_name
    " "$DB_NAME" 2>/dev/null || echo "")

    if [ -n "$THREADLINE_TABLES" ]; then
        log_success "Migration completed, found following threadline tables:"
        echo "$THREADLINE_TABLES" | while read table; do
            if [ -n "$table" ]; then
                count=$($MARIADB_CMD -s -e "SELECT COUNT(*) FROM \`$table\`" "$DB_NAME" 2>/dev/null || echo "0")
                log_info "  - $table ($count records)"
            fi
        done
    else
        log_error "Migration failed, no threadline tables found"
        exit 1
    fi
}

# Show help information
show_help() {
    echo "MariaDB Migration Script: jirabot to threadline"
    echo "============================================="
    echo ""
    echo "IMPORTANT: This script is SPECIFICALLY designed for migrating from 'jirabot'"
    echo "to 'threadline' in this Django project. It is NOT a generic migration tool."
    echo ""
    echo "Background: The original name 'jirabot' was too restrictive and couldn't"
    echo "encompass all the application's functionality. The app has evolved beyond"
    echo "just Jira integration to become a comprehensive threadline management platform."
    echo ""
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  -h, --help     Show this help information"
    echo "  -d, --dry-run  Preview mode, do not execute actual migration"
    echo "  -c, --check    Only check status, do not execute migration"
    echo "  -r, --remove   Delete original jirabot tables after migration"
    echo "  -f, --force    Force migration even if threadline tables exist"
    echo ""
    echo "Environment Variables:"
    echo "  MYSQL_HOST     Database host (default: localhost)"
    echo "  MYSQL_PORT     Database port (default: 3306)"
    echo "  MYSQL_DATABASE Database name (default: devify)"
    echo "  MYSQL_USER     Database username (required)"
    echo "  MYSQL_PASSWORD Database password"
    echo ""
    echo "Examples:"
    echo "  MYSQL_USER=root MYSQL_PASSWORD=mypass $0"
    echo "  $0 --dry-run"
    echo "  $0 --check"
    echo "  $0 --remove"
}

# Main function
main() {
    # Parse command line arguments
    DRY_RUN=false
    CHECK_ONLY=false
    REMOVE_ORIGINAL=false
    FORCE_MIGRATION=false

    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_help
                exit 0
                ;;
            -d|--dry-run)
                DRY_RUN=true
                shift
                ;;
            -c|--check)
                CHECK_ONLY=true
                shift
                ;;
            -r|--remove)
                REMOVE_ORIGINAL=true
                shift
                ;;
            -f|--force)
                FORCE_MIGRATION=true
                shift
                ;;
            *)
                log_error "Unknown parameter: $1"
                show_help
                exit 1
                ;;
        esac

    done

    log_info "=== MariaDB Migration Script Started ==="
    log_info "IMPORTANT: This script is SPECIFICALLY for jirabot → threadline migration"
    log_info "It is NOT a generic Django app renaming tool!"

    # Check environment variables
    check_environment

    # Check dependencies
    check_mariadb_client

    # Test connection
    test_connection

    # Check status
    check_current_state

    if [ "$CHECK_ONLY" = true ]; then
        log_info "Check mode, exiting"
        exit 0
    fi

    # Check if threadline tables already exist
    THREADLINE_TABLES=$($MARIADB_CMD -s -e "
        SELECT table_name FROM information_schema.tables
        WHERE table_schema = '$DB_NAME' AND table_name LIKE 'threadline_%'
        ORDER BY table_name
    " "$DB_NAME" 2>/dev/null || echo "")

    if [ -n "$THREADLINE_TABLES" ] && [ "$FORCE_MIGRATION" != true ]; then
        log_warning "Threadline tables already exist"
        log_info "Use --force flag if you want to proceed anyway"
        exit 1
    fi

    if [ "$DRY_RUN" = true ]; then
        log_info "Preview mode, do not execute actual migration"
        log_info "Operations to be performed:"
        log_info "  1. Create threadline table structure"
        log_info "  2. Migrate data using INSERT ... SELECT"
        log_info "  3. Update Django migration history"
        if [ "$REMOVE_ORIGINAL" = true ]; then
            log_info "  4. Delete original jirabot tables"
        fi
        exit 0
    fi

    # Execute migration
    create_threadline_tables
    migrate_data
    update_migration_history

    # Drop original tables (optional)
    if [ "$REMOVE_ORIGINAL" = true ]; then
        drop_jirabot_tables
    fi

    # Verify results
    verify_migration

    log_success "=== Migration Completed ==="
}

# Run main function
main "$@"
