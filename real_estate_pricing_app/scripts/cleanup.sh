#!/bin/bash

# Cleanup Script for Real Estate Pricing Advisor
# Destroys the CDK stack and cleans up resources

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
ENVIRONMENT="dev"
PROFILE=""
REGION="us-east-1"

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

show_usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Destroy the Real Estate Pricing Advisor stack and clean up resources

OPTIONS:
    -e, --environment ENV       Environment to destroy (dev, staging, prod) [default: dev]
    -p, --profile PROFILE       AWS CLI profile to use (optional)
    -r, --region REGION         AWS region [default: us-east-1]
    -f, --force                 Skip confirmation prompt
    -h, --help                  Show this help message

EXAMPLES:
    $0 -e dev                   # Destroy dev environment
    $0 -e prod -f               # Destroy prod without confirmation

WARNING: This will permanently delete all resources in the stack!

EOF
}

FORCE=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -e|--environment)
            ENVIRONMENT="$2"
            shift 2
            ;;
        -p|--profile)
            PROFILE="$2"
            shift 2
            ;;
        -r|--region)
            REGION="$2"
            shift 2
            ;;
        -f|--force)
            FORCE=true
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

# Set AWS profile if provided
if [[ -n "$PROFILE" ]]; then
    export AWS_PROFILE="$PROFILE"
fi

export AWS_DEFAULT_REGION="$REGION"

STACK_NAME="PricingAppStack-$ENVIRONMENT"

# Confirmation prompt
if [[ "$FORCE" == false ]]; then
    print_warning "This will destroy the stack: $STACK_NAME"
    print_warning "All resources including data in DynamoDB will be permanently deleted!"
    read -p "Are you sure you want to continue? (yes/no): " confirm
    
    if [[ "$confirm" != "yes" ]]; then
        print_status "Cleanup cancelled"
        exit 0
    fi
fi

print_status "Destroying stack: $STACK_NAME"

cdk destroy $STACK_NAME --context environment=$ENVIRONMENT --force

print_success "Stack destroyed successfully!"
