#!/bin/bash

# This script is used to:
# 1. Rename the project name (e.g., from 'mito' to 'newname')
# 2. Rename the Django project directory (e.g., from 'api' to 'newapi')
#
# Usage:
#   ./project_manager.sh --project-name <new_name>     # Rename project
#   ./project_manager.sh --django-project-name <new_name>  # Rename Django project
#   ./project_manager.sh --dry-run                     # Show what would be changed
#
# Example:
#   ./project_manager.sh --project-name myproject --dry-run
#   ./project_manager.sh --django-project-name myapi --dry-run
#   ./project_manager.sh --project-name myproject --django-project-name myapi

# Get absolute path of current directory
CURRENT_PATH=$(cd "$(dirname "$0")/.." && pwd)
cd "$CURRENT_PATH"

# Default values
DRY_RUN=false
PROJECT_OLD_NAME="mito"
PROJECT_NEW_NAME=""
DJANGO_PROJECT_OLD_NAME="mito"
DJANGO_PROJECT_NEW_NAME=""

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo "Options:"
    echo "  --project-name <name>          New project name (letters and numbers only)"
    echo "  --django-project-name <name>   New Django project name (letters, numbers and underscores only)"
    echo "  --dry-run                      Show what would be changed without making changes"
    echo "  --help                         Show this help message"
    exit 1
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --project-name)
            PROJECT_NEW_NAME="$2"
            shift 2
            ;;
        --django-project-name)
            DJANGO_PROJECT_NEW_NAME="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --help)
            show_usage
            ;;
        *)
            echo "Unknown option: $1"
            show_usage
            ;;
    esac
done

# Validate inputs
if [[ -z "$PROJECT_NEW_NAME" && -z "$DJANGO_PROJECT_NEW_NAME" ]]; then
    echo "Error: Either --project-name or --django-project-name must be specified"
    show_usage
fi

# Validate project name format
if [[ -n "$PROJECT_NEW_NAME" && ! "$PROJECT_NEW_NAME" =~ ^[a-zA-Z][a-zA-Z0-9_]*$ ]]; then
    echo "Error: Project name must:"
    echo "- Start with a letter"
    echo "- Only contain letters, numbers and underscores"
    exit 1
fi

# Validate django project name format
if [[ -n "$DJANGO_PROJECT_NEW_NAME" && ! "$DJANGO_PROJECT_NEW_NAME" =~ ^[a-zA-Z][a-zA-Z0-9_]*$ ]]; then
    echo "Error: Django project name must:"
    echo "- Start with a letter"
    echo "- Only contain letters, numbers and underscores"
    exit 1
fi

# Function to replace project name in specific files with exact matches
replace_project_name() {
    if [[ -n "$PROJECT_NEW_NAME" ]]; then
        local files_to_replace=(
            "pyproject.toml"
            ".env.sample"
            ".env"
            ".gitignore"
            "docker-compose.yml"
            "docker-compose.dev.yml"
            "docker-compose.prod.yml"
            "000-create-databases.sql"
            "docker/nginx/default.conf"
            "docker/mysql/initdb.d/000-create-databases.sql"
        )

        if [[ "$DRY_RUN" = true ]]; then
            echo "Would replace '$PROJECT_OLD_NAME' with '$PROJECT_NEW_NAME' in:"
            for file in "${files_to_replace[@]}"; do
                echo "  - $file"
            done
        else
            # Replace exact matches of project name in specific files
            for file in "${files_to_replace[@]}"; do
                local full_path="${CURRENT_PATH}/${file}"
                if [[ -f "$full_path" ]]; then
                    sed -i "s/\b${PROJECT_OLD_NAME}/${PROJECT_NEW_NAME}/g" "$full_path" 2>/dev/null || true
                fi
            done
        fi
    fi
}

# Function to replace Django project name in specific files with exact matches
replace_django_project_name() {
    if [[ -n "$DJANGO_PROJECT_NEW_NAME" ]]; then
        # Define file paths and their corresponding replacement patterns with absolute paths
        declare -A replacements=(
            ["${CURRENT_PATH}/docker-compose.*.yml"]="dockerfile: ${DJANGO_PROJECT_OLD_NAME}/Dockerfile|dockerfile: ${DJANGO_PROJECT_NEW_NAME}/Dockerfile"
            ["${CURRENT_PATH}/MANIFEST.in"]="recursive-include ${DJANGO_PROJECT_OLD_NAME}|recursive-include ${DJANGO_PROJECT_NEW_NAME}"
            ["${CURRENT_PATH}/pyproject.toml"]="packages = \\[\"${DJANGO_PROJECT_OLD_NAME}\"\\]|packages = \\[\"${DJANGO_PROJECT_NEW_NAME}\"\\]"
            ["${CURRENT_PATH}/tox.ini"]="flake8 ${DJANGO_PROJECT_OLD_NAME}|flake8 ${DJANGO_PROJECT_NEW_NAME}"
            ["${CURRENT_PATH}/api/Dockerfile"]="ENV DJANGO_PROJECT_DIR=${DJANGO_PROJECT_OLD_NAME}|ENV DJANGO_PROJECT_DIR=${DJANGO_PROJECT_NEW_NAME}"
        )

        if [[ "$DRY_RUN" = true ]]; then
            # Display files that would be modified
            echo "Would replace '$DJANGO_PROJECT_OLD_NAME' with '$DJANGO_PROJECT_NEW_NAME' in:"
            for file in "${!replacements[@]}"; do
                echo "  - $file"
            done
            echo "Would rename directory: $DJANGO_PROJECT_OLD_NAME -> $DJANGO_PROJECT_NEW_NAME"
        else
            # Perform replacements in files
            for file_pattern in "${!replacements[@]}"; do
                local pattern="${replacements[$file_pattern]}"
                local search="${pattern%|*}"
                local replace="${pattern#*|}"

                # Use wildcard to match filenames
                for matched_file in $file_pattern; do
                    if [[ -f "$matched_file" ]]; then
                        sed -i "s|$search|$replace|g" "$matched_file" 2>/dev/null || true
                    fi
                done
            done

            # Rename Django project directory using absolute path
            if [ -d "${CURRENT_PATH}/${DJANGO_PROJECT_OLD_NAME}" ]; then
                mv "${CURRENT_PATH}/${DJANGO_PROJECT_OLD_NAME}" "${CURRENT_PATH}/${DJANGO_PROJECT_NEW_NAME}"
            else
                echo "Error: Directory '${CURRENT_PATH}/${DJANGO_PROJECT_OLD_NAME}' not found"
                exit 1
            fi
        fi
    fi
}

# Main execution
if [[ "$DRY_RUN" = true ]]; then
    echo "=== DRY RUN MODE - No changes will be made ==="
fi

# Execute based on provided options
if [[ -n "$PROJECT_NEW_NAME" ]]; then
    replace_project_name
fi

if [[ -n "$DJANGO_PROJECT_NEW_NAME" ]]; then
    replace_django_project_name
fi

if [[ "$DRY_RUN" = true ]]; then
    echo "=== DRY RUN COMPLETE - No changes were made ==="
else
    echo "=== Changes completed successfully ==="
    if [[ -n "$PROJECT_NEW_NAME" ]]; then
        echo "Project renamed from $PROJECT_OLD_NAME to $PROJECT_NEW_NAME"
    fi
    if [[ -n "$DJANGO_PROJECT_NEW_NAME" ]]; then
        echo "Django project renamed from $DJANGO_PROJECT_OLD_NAME to $DJANGO_PROJECT_NEW_NAME"
        echo "All configuration files have been updated"
    fi
fi
