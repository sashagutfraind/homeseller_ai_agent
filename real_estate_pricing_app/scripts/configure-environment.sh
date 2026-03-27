#!/bin/bash

# Environment Configuration Script for Real Estate Pricing Advisor
# This script configures environment-specific settings

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
ENVIRONMENT="dev"
CDK_FILE="cdk.json"

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
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

# Function to show usage
show_usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Configure environment-specific settings for Real Estate Pricing Advisor

OPTIONS:
    -e, --environment ENV       Environment to configure (dev, staging, prod) [default: dev]
    -d, --domain DOMAIN         Set custom domain name for the environment
    -a, --account ACCOUNT       Set AWS account ID for the environment
    -r, --region REGION         Set AWS region for the environment [default: us-east-1]
    --list                      List all configured environments
    -h, --help                  Show this help message

EXAMPLES:
    $0 -e prod -d pricing.example.com -a 123456789012    # Configure production
    $0 -e staging -d staging.pricing.example.com         # Configure staging
    $0 --list                                            # List all environments

EOF
}

# Function to validate environment name
validate_environment() {
    if [[ ! "$1" =~ ^(dev|staging|prod)$ ]]; then
        print_error "Invalid environment: $1. Must be one of: dev, staging, prod"
        exit 1
    fi
}

# Function to validate AWS account ID
validate_account_id() {
    if [[ ! "$1" =~ ^[0-9]{12}$ ]]; then
        print_error "Invalid AWS account ID: $1. Must be 12 digits."
        exit 1
    fi
}

# Function to validate domain name
validate_domain() {
    if [[ ! "$1" =~ ^[a-zA-Z0-9][a-zA-Z0-9-]{1,61}[a-zA-Z0-9]\.[a-zA-Z]{2,}$ ]]; then
        print_error "Invalid domain name: $1"
        exit 1
    fi
}

# Function to list all configured environments
list_environments() {
    print_status "Configured environments:"
    echo
    
    if [[ -f "$CDK_FILE" ]]; then
        echo "=== CDK Configuration (cdk.json) ==="
        if jq -e '.context.environments' "$CDK_FILE" >/dev/null 2>&1; then
            jq -r '.context.environments | keys[]' "$CDK_FILE" | while read env; do
                domain=$(jq -r ".context.environments.$env.domainName // \"none\"" "$CDK_FILE")
                cors=$(jq -r ".context.environments.$env.corsOrigins[0] // \"*\"" "$CDK_FILE")
                echo "  $env: domain=$domain, cors=$cors"
            done
        else
            print_warning "No environments configured yet"
        fi
        echo
    fi
}

# Function to update environment configuration
update_environment_config() {
    local env="$1"
    local domain="$2"
    local account="$3"
    local region="$4"
    
    print_status "Updating configuration for environment: $env"
    
    # Ensure environments context exists
    if ! jq -e '.context.environments' "$CDK_FILE" >/dev/null 2>&1; then
        print_status "Creating environments configuration..."
        jq '.context.environments = {}' "$CDK_FILE" > "${CDK_FILE}.tmp" && mv "${CDK_FILE}.tmp" "$CDK_FILE"
    fi
    
    # Ensure environment entry exists
    if ! jq -e ".context.environments.$env" "$CDK_FILE" >/dev/null 2>&1; then
        print_status "Creating configuration for $env environment..."
        jq ".context.environments.$env = {}" "$CDK_FILE" > "${CDK_FILE}.tmp" && mv "${CDK_FILE}.tmp" "$CDK_FILE"
    fi
    
    # Update domain name
    if [[ -n "$domain" ]]; then
        print_status "Setting domain name: $domain"
        jq ".context.environments.$env.domainName = \"$domain\"" "$CDK_FILE" > "${CDK_FILE}.tmp" && mv "${CDK_FILE}.tmp" "$CDK_FILE"
    fi
    
    # Update account ID
    if [[ -n "$account" ]]; then
        print_status "Setting AWS account ID: $account"
        jq ".context.environments.$env.account = \"$account\"" "$CDK_FILE" > "${CDK_FILE}.tmp" && mv "${CDK_FILE}.tmp" "$CDK_FILE"
    fi
    
    # Update region
    if [[ -n "$region" ]]; then
        print_status "Setting AWS region: $region"
        jq ".context.environments.$env.region = \"$region\"" "$CDK_FILE" > "${CDK_FILE}.tmp" && mv "${CDK_FILE}.tmp" "$CDK_FILE"
    fi
    
    print_success "Configuration updated for environment: $env"
}

# Parse command line arguments
DOMAIN=""
ACCOUNT=""
REGION=""
LIST_ONLY=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -e|--environment)
            ENVIRONMENT="$2"
            shift 2
            ;;
        -d|--domain)
            DOMAIN="$2"
            shift 2
            ;;
        -a|--account)
            ACCOUNT="$2"
            shift 2
            ;;
        -r|--region)
            REGION="$2"
            shift 2
            ;;
        --list)
            LIST_ONLY=true
            shift
            ;;
        -h|--help)
            show_usage
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Check if we're in the right directory
if [[ ! -f "package.json" ]]; then
    print_error "package.json not found. Please run this script from the project root directory."
    exit 1
fi

# Check if jq is installed
if ! command -v jq &> /dev/null; then
    print_error "jq is not installed. Please install jq to use this script."
    print_status "On macOS: brew install jq"
    print_status "On Ubuntu/Debian: sudo apt-get install jq"
    exit 1
fi

# Handle list command
if [[ "$LIST_ONLY" == true ]]; then
    list_environments
    exit 0
fi

# Validate inputs
validate_environment "$ENVIRONMENT"

if [[ -n "$DOMAIN" ]]; then
    validate_domain "$DOMAIN"
fi

if [[ -n "$ACCOUNT" ]]; then
    validate_account_id "$ACCOUNT"
fi

# Update configuration
update_environment_config "$ENVIRONMENT" "$DOMAIN" "$ACCOUNT" "$REGION"

print_success "Environment configuration completed successfully!"
echo
echo "=== Updated Configuration ==="
echo "Environment: $ENVIRONMENT"
if [[ -n "$DOMAIN" ]]; then
    echo "Domain: $DOMAIN"
fi
if [[ -n "$ACCOUNT" ]]; then
    echo "AWS Account: $ACCOUNT"
fi
if [[ -n "$REGION" ]]; then
    echo "AWS Region: $REGION"
fi
echo
echo "You can now deploy using: ./scripts/deploy.sh -e $ENVIRONMENT"
