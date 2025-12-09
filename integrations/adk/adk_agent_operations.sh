#!/bin/bash
# =============================================================================
# Zscaler MCP Agent Operations Script
# 
# This script provides operations for running and deploying the Zscaler MCP
# Agent with Google ADK to Cloud Run, Vertex AI Agent Engine, and Agentspace.
#
# Usage: ./adk_agent_operations.sh [operation]
#
# Operations:
#   local_run           - Run the agent locally for development
#   cloudrun_deploy     - Deploy to Google Cloud Run
#   agent_engine_deploy - Deploy to Vertex AI Agent Engine
#   agentspace_register - Register deployed agent with Agentspace
#
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AGENT_DIR="${SCRIPT_DIR}/zscaler_agent"
ENV_FILE="${AGENT_DIR}/.env"
ENV_TEMPLATE="${AGENT_DIR}/env.properties"
ENV_BACKUP="${AGENT_DIR}/.env.bak"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# -----------------------------------------------------------------------------
# Helper Functions
# -----------------------------------------------------------------------------

log_info() {
    echo -e "${BLUE}INFO:${NC} $1"
}

log_success() {
    echo -e "${GREEN}SUCCESS:${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}WARNING:${NC} $1"
}

log_error() {
    echo -e "${RED}ERROR:${NC} $1"
}

check_env_var() {
    local var_name=$1
    local var_value="${!var_name}"
    
    if [[ -z "$var_value" || "$var_value" == "NOT_SET" ]]; then
        log_error "Variable '$var_name' is not set or invalid."
        return 1
    fi
    log_info "Variable '$var_name' is set and valid."
    return 0
}

load_env_file() {
    if [[ ! -f "$ENV_FILE" ]]; then
        log_error "Environment file '$ENV_FILE' not found."
        return 1
    fi
    
    echo "--- Loading environment variables from '$ENV_FILE' ---"
    set -a
    source "$ENV_FILE"
    set +a
    echo "--- Environment variables loaded. ---"
}

backup_env_file() {
    if [[ -f "$ENV_FILE" ]]; then
        log_info "Backing up '$ENV_FILE' to '$ENV_BACKUP'."
        cp "$ENV_FILE" "$ENV_BACKUP"
    fi
}

restore_env_file() {
    if [[ -f "$ENV_BACKUP" ]]; then
        log_info "Restoring .env file from backup: '$ENV_BACKUP'."
        mv "$ENV_BACKUP" "$ENV_FILE"
    fi
}

prepare_vertex_env() {
    backup_env_file
    log_info "Modifying '$ENV_FILE': Removing GOOGLE_API_KEY and setting GOOGLE_GENAI_USE_VERTEXAI=True."
    
    # Remove GOOGLE_API_KEY and set GOOGLE_GENAI_USE_VERTEXAI=True
    sed -i.tmp '/^GOOGLE_API_KEY=/d' "$ENV_FILE"
    sed -i.tmp 's/^GOOGLE_GENAI_USE_VERTEXAI=.*/GOOGLE_GENAI_USE_VERTEXAI=True/' "$ENV_FILE"
    rm -f "${ENV_FILE}.tmp"
    
    log_info "Re-loading modified environment variables."
    load_env_file
}

# -----------------------------------------------------------------------------
# Validation Functions
# -----------------------------------------------------------------------------

validate_local_run() {
    echo "--- Validating required environment variables for 'local_run' mode ---"
    local failed=0
    
    check_env_var "GOOGLE_GENAI_USE_VERTEXAI" || failed=1
    check_env_var "GOOGLE_API_KEY" || failed=1
    check_env_var "GOOGLE_MODEL" || failed=1
    check_env_var "ZSCALER_CLIENT_ID" || failed=1
    check_env_var "ZSCALER_CLIENT_SECRET" || failed=1
    check_env_var "ZSCALER_VANITY_DOMAIN" || failed=1
    check_env_var "ZSCALER_AGENT_PROMPT" || failed=1
    
    if [[ $failed -eq 1 ]]; then
        echo "--- Some required environment variables are MISSING or INVALID. ---"
        return 1
    fi
    echo "--- All required environment variables are VALID. ---"
    return 0
}

validate_cloudrun_deploy() {
    echo "--- Validating required environment variables for 'cloudrun_deploy' mode ---"
    local failed=0
    
    check_env_var "GOOGLE_GENAI_USE_VERTEXAI" || failed=1
    check_env_var "GOOGLE_MODEL" || failed=1
    check_env_var "ZSCALER_CLIENT_ID" || failed=1
    check_env_var "ZSCALER_CLIENT_SECRET" || failed=1
    check_env_var "ZSCALER_VANITY_DOMAIN" || failed=1
    check_env_var "ZSCALER_AGENT_PROMPT" || failed=1
    check_env_var "PROJECT_ID" || failed=1
    check_env_var "REGION" || failed=1
    
    if [[ $failed -eq 1 ]]; then
        echo "--- Some required environment variables are MISSING or INVALID. ---"
        return 1
    fi
    echo "--- All required environment variables are VALID. ---"
    return 0
}

validate_agent_engine_deploy() {
    echo "--- Validating required environment variables for 'agent_engine_deploy' mode ---"
    local failed=0
    
    check_env_var "GOOGLE_GENAI_USE_VERTEXAI" || failed=1
    check_env_var "GOOGLE_MODEL" || failed=1
    check_env_var "ZSCALER_CLIENT_ID" || failed=1
    check_env_var "ZSCALER_CLIENT_SECRET" || failed=1
    check_env_var "ZSCALER_VANITY_DOMAIN" || failed=1
    check_env_var "ZSCALER_AGENT_PROMPT" || failed=1
    check_env_var "PROJECT_ID" || failed=1
    check_env_var "REGION" || failed=1
    check_env_var "AGENT_ENGINE_STAGING_BUCKET" || failed=1
    
    if [[ $failed -eq 1 ]]; then
        echo "--- Some required environment variables are MISSING or INVALID. ---"
        return 1
    fi
    echo "--- All required environment variables are VALID. ---"
    return 0
}

validate_agentspace_register() {
    echo "--- Validating required environment variables for 'agentspace_register' mode ---"
    local failed=0
    
    check_env_var "GOOGLE_GENAI_USE_VERTEXAI" || failed=1
    check_env_var "GOOGLE_MODEL" || failed=1
    check_env_var "ZSCALER_CLIENT_ID" || failed=1
    check_env_var "ZSCALER_CLIENT_SECRET" || failed=1
    check_env_var "ZSCALER_VANITY_DOMAIN" || failed=1
    check_env_var "ZSCALER_AGENT_PROMPT" || failed=1
    check_env_var "PROJECT_ID" || failed=1
    check_env_var "REGION" || failed=1
    check_env_var "PROJECT_NUMBER" || failed=1
    check_env_var "AGENT_LOCATION" || failed=1
    check_env_var "REASONING_ENGINE_NUMBER" || failed=1
    check_env_var "AGENT_SPACE_APP_NAME" || failed=1
    
    if [[ $failed -eq 1 ]]; then
        echo "--- Some required environment variables are MISSING or INVALID. ---"
        return 1
    fi
    echo "--- All required environment variables are VALID. ---"
    return 0
}

# -----------------------------------------------------------------------------
# Operation Functions
# -----------------------------------------------------------------------------

do_local_run() {
    log_info "Running ADK Agent for local development..."
    # ADK needs to run from parent directory to discover agent packages
    cd "$SCRIPT_DIR"
    adk web
}

do_cloudrun_deploy() {
    log_info "Preparing for Cloud Run deployment..."
    prepare_vertex_env
    
    log_info "Deploying ADK Agent to Cloud Run..."
    cd "$SCRIPT_DIR"
    
    adk deploy cloud_run \
        --project "$PROJECT_ID" \
        --region "$REGION" \
        --service_name "zscaler-mcp-agent" \
        --with_ui \
        ./zscaler_agent
    
    log_success "Cloud Run deployment completed successfully."
}

do_agent_engine_deploy() {
    log_info "Preparing for Agent Engine deployment..."
    prepare_vertex_env
    
    log_info "Deploying ADK Agent to Agent Engine..."
    cd "$SCRIPT_DIR"
    
    adk deploy agent_engine \
        --project "$PROJECT_ID" \
        --region "$REGION" \
        --staging_bucket "$AGENT_ENGINE_STAGING_BUCKET" \
        --display_name "zscaler_agent" \
        ./zscaler_agent
    
    log_success "Agent Engine deployment completed successfully."
}

do_agentspace_register() {
    log_info "Registering ADK Agent with AgentSpace..."
    
    local API_URL
    API_URL="https://discoveryengine.googleapis.com/v1alpha/projects/${PROJECT_ID}/locations/${AGENT_LOCATION}/collections/default_collection/engines/${AGENT_SPACE_APP_NAME}/assistants/default_assistant/agents"
    
    log_info "Sending POST request to: $API_URL"
    
    local REQUEST_BODY
    REQUEST_BODY=$(cat <<EOF
{
    "displayName": "Zscaler MCP Agent",
    "description": "Allows users to interact with Zscaler Zero Trust Exchange platform",
    "adk_agent_definition": {
        "tool_settings": {
            "tool_description": "Zscaler security tools for ZIA, ZPA, ZDX, ZCC, EASM, and ZIdentity"
        },
        "provisioned_reasoning_engine": {
            "reasoning_engine": "projects/${PROJECT_NUMBER}/locations/${REGION}/reasoningEngines/${REASONING_ENGINE_NUMBER}"
        }
    }
}
EOF
)
    
    echo "DEBUG: Request Body:"
    echo "$REQUEST_BODY" | jq .
    
    local RESPONSE
    RESPONSE=$(curl -s -X POST \
        -H "Authorization: Bearer $(gcloud auth print-access-token)" \
        -H "Content-Type: application/json" \
        -H "X-Goog-User-Project: $PROJECT_ID" \
        -d "$REQUEST_BODY" \
        "$API_URL")
    
    echo "$RESPONSE" | jq .
    
    if echo "$RESPONSE" | jq -e '.name' > /dev/null 2>&1; then
        log_success "AgentSpace registration completed successfully."
    else
        log_error "AgentSpace registration may have failed. Check the response above."
        return 1
    fi
}

# -----------------------------------------------------------------------------
# Main Entry Point
# -----------------------------------------------------------------------------

main() {
    local operation="${1:-}"
    
    # Check if .env file exists, if not create from template
    if [[ ! -f "$ENV_FILE" ]]; then
        if [[ -f "$ENV_TEMPLATE" ]]; then
            log_info "No .env file found. Creating from template..."
            cp "$ENV_TEMPLATE" "$ENV_FILE"
            log_success "'$ENV_TEMPLATE' copied to '$ENV_FILE'."
            log_warning "ACTION REQUIRED: Please update the variables in '$ENV_FILE' before running this script with an operation mode."
            exit 0
        else
            log_error "Neither '$ENV_FILE' nor '$ENV_TEMPLATE' found."
            exit 1
        fi
    fi
    
    # If no operation provided, show help
    if [[ -z "$operation" ]]; then
        echo ""
        echo "Usage: $0 [operation]"
        echo ""
        echo "Operations:"
        echo "  local_run           - Run the agent locally for development"
        echo "  cloudrun_deploy     - Deploy to Google Cloud Run"
        echo "  agent_engine_deploy - Deploy to Vertex AI Agent Engine"
        echo "  agentspace_register - Register deployed agent with Agentspace"
        echo ""
        exit 0
    fi
    
    log_info "Operation mode selected: '$operation'."
    
    # Load environment
    load_env_file || exit 1
    
    # Execute operation
    case "$operation" in
        local_run)
            validate_local_run || exit 1
            do_local_run
            ;;
        cloudrun_deploy)
            validate_cloudrun_deploy || exit 1
            do_cloudrun_deploy
            restore_env_file
            ;;
        agent_engine_deploy)
            validate_agent_engine_deploy || exit 1
            do_agent_engine_deploy
            restore_env_file
            ;;
        agentspace_register)
            validate_agentspace_register || exit 1
            do_agentspace_register
            ;;
        *)
            log_error "Unknown operation: '$operation'"
            echo "Valid operations: local_run, cloudrun_deploy, agent_engine_deploy, agentspace_register"
            exit 1
            ;;
    esac
    
    echo "--- Operation '$operation' complete. ---"
}

# Run main function
main "$@"

