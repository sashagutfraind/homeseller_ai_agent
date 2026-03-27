#!/bin/bash

# Real Estate Pricing Advisor Deployment Script
# This script deploys the entire application to AWS using CDK

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
ENVIRONMENT="dev"
DOMAIN_NAME=""
SKIP_FRONTEND_BUILD=false
PROFILE=""
REGION="us-east-1"

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

Deploy the Real Estate Pricing Advisor application

OPTIONS:
    -e, --environment ENV       Deployment environment (dev, staging, prod) [default: dev]
    -d, --domain DOMAIN         Custom domain name (optional)
    -p, --profile PROFILE       AWS CLI profile to use (optional)
    -r, --region REGION         AWS region [default: us-east-1]
    --skip-frontend-build       Skip frontend build step
    -h, --help                 Show this help message

EXAMPLES:
    $0                                          # Deploy to dev environment
    $0 -e prod -d pricing.example.com          # Deploy to prod with custom domain
    $0 -e staging -p my-aws-profile            # Deploy to staging with specific AWS profile

PREREQUISITES:
    - AWS CLI configured with appropriate credentials
    - Node.js and pnpm installed
    - CDK CLI installed (pnpm add -g aws-cdk)
    - Bedrock access enabled for Claude Haiku 4.5 in your AWS account

EOF
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -e|--environment)
            ENVIRONMENT="$2"
            shift 2
            ;;
        -d|--domain)
            DOMAIN_NAME="$2"
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
        --skip-frontend-build)
            SKIP_FRONTEND_BUILD=true
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

# Validate environment
if [[ ! "$ENVIRONMENT" =~ ^(dev|staging|prod)$ ]]; then
    print_error "Invalid environment: $ENVIRONMENT. Must be one of: dev, staging, prod"
    exit 1
fi

print_status "Starting deployment for environment: $ENVIRONMENT"

# Set AWS profile if provided
if [[ -n "$PROFILE" ]]; then
    export AWS_PROFILE="$PROFILE"
    print_status "Using AWS profile: $PROFILE"
fi

# Set AWS region
export AWS_DEFAULT_REGION="$REGION"
export CDK_DEFAULT_REGION="$REGION"
print_status "Using AWS region: $REGION"

# Check prerequisites
print_status "Checking prerequisites..."

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    print_error "AWS CLI is not installed. Please install it first."
    exit 1
fi

# Check AWS credentials
if ! aws sts get-caller-identity &> /dev/null; then
    print_error "AWS credentials not configured or invalid. Please run 'aws configure' or set AWS_PROFILE."
    exit 1
fi

# Check if pnpm is installed
if ! command -v pnpm &> /dev/null; then
    print_error "pnpm is not installed. Please install it with: npm install -g pnpm"
    exit 1
fi

# Check if CDK is installed
if ! command -v cdk &> /dev/null; then
    print_error "AWS CDK is not installed. Please install it with: pnpm add -g aws-cdk"
    exit 1
fi

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    print_error "Node.js is not installed. Please install Node.js first."
    exit 1
fi

# Check if we're in the right directory
if [[ ! -f "cdk.json" ]]; then
    print_error "cdk.json not found. Please run this script from the project root directory."
    exit 1
fi

print_success "Prerequisites check passed"

# Get AWS account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
export CDK_DEFAULT_ACCOUNT="$ACCOUNT_ID"
print_status "AWS Account ID: $ACCOUNT_ID"

# Install dependencies
print_status "Installing CDK dependencies..."
pnpm install

# Bootstrap CDK if needed
print_status "Checking CDK bootstrap status..."
if ! aws cloudformation describe-stacks --stack-name CDKToolkit --region "$REGION" &> /dev/null; then
    print_status "Bootstrapping CDK for account $ACCOUNT_ID in region $REGION..."
    cdk bootstrap aws://$ACCOUNT_ID/$REGION
else
    print_status "CDK already bootstrapped"
fi

# Build frontend if not skipped
if [[ "$SKIP_FRONTEND_BUILD" == false ]]; then
    print_status "Building frontend application..."
    cd frontend
    
    # Install frontend dependencies
    if [[ ! -d "node_modules" ]]; then
        print_status "Installing frontend dependencies..."
        pnpm install
    fi
    
    # Build frontend
    pnpm run build
    
    cd ..
    print_success "Frontend build completed"
else
    print_warning "Skipping frontend build"
fi

# Deploy CDK stack
print_status "Deploying CDK stack..."

# Prepare CDK context
CDK_CONTEXT="--context environment=$ENVIRONMENT"

if [[ -n "$DOMAIN_NAME" ]]; then
    CDK_CONTEXT="$CDK_CONTEXT --context domainName=$DOMAIN_NAME"
fi

# Deploy the stack
STACK_NAME="PricingAppStack-$ENVIRONMENT"

print_status "Deploying stack: $STACK_NAME"
cdk deploy $STACK_NAME $CDK_CONTEXT --require-approval never

print_success "CDK deployment completed"

# Get stack outputs
print_status "Retrieving stack outputs..."
OUTPUTS=$(aws cloudformation describe-stacks --stack-name "$STACK_NAME" --region "$REGION" --query 'Stacks[0].Outputs' --output json)

# Extract important outputs
WEBSITE_URL=$(echo "$OUTPUTS" | jq -r '.[] | select(.OutputKey=="WebsiteURL") | .OutputValue // "N/A"')
API_URL=$(echo "$OUTPUTS" | jq -r '.[] | select(.OutputKey=="ApiUrl") | .OutputValue // "N/A"')
USER_POOL_ID=$(echo "$OUTPUTS" | jq -r '.[] | select(.OutputKey=="UserPoolId") | .OutputValue // "N/A"')
USER_POOL_CLIENT_ID=$(echo "$OUTPUTS" | jq -r '.[] | select(.OutputKey=="UserPoolClientId") | .OutputValue // "N/A"')
IDENTITY_POOL_ID=$(echo "$OUTPUTS" | jq -r '.[] | select(.OutputKey=="IdentityPoolId") | .OutputValue // "N/A"')

print_success "Deployment completed successfully!"
echo
echo "=== Deployment Information ==="
echo "Environment: $ENVIRONMENT"
echo "Website URL: $WEBSITE_URL"
echo "API URL: $API_URL"
echo "User Pool ID: $USER_POOL_ID"
echo "User Pool Client ID: $USER_POOL_CLIENT_ID"
echo "Identity Pool ID: $IDENTITY_POOL_ID"
echo "AWS Region: $REGION"
echo "AWS Account: $ACCOUNT_ID"
echo

print_success "Deployment script completed successfully!"

# Show next steps
echo
echo "=== Next Steps ==="
echo "1. Visit $WEBSITE_URL to test the application"
echo "2. Ensure Bedrock model access is enabled:"
echo "   - Go to AWS Bedrock console in $REGION"
echo "   - Navigate to 'Model access'"
echo "   - Enable 'Claude Haiku 4.5' (us.anthropic.claude-haiku-4-5-20251001-v1:0)"
echo "3. Check CloudWatch logs for any issues"
echo "4. Register a new user account to start using the pricing advisor"
echo
echo "For troubleshooting, check the deployment logs above and AWS CloudFormation console."
