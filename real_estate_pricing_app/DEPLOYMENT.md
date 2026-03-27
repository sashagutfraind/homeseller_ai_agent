# Deployment Guide

## Prerequisites

1. AWS Account with Bedrock access (Claude Haiku 4.5 enabled in us-east-1)
2. AWS CLI configured with credentials
3. Node.js 18+ and pnpm installed
   - Install pnpm: `npm install -g pnpm` or `corepack enable`
4. AWS CDK CLI installed: `pnpm add -g aws-cdk`

## Step 1: Install Dependencies

```bash
# Install CDK dependencies
pnpm install

# Install frontend dependencies
cd frontend
pnpm install
cd ..
```

## Step 2: Bootstrap CDK (First Time Only)

```bash
cdk bootstrap aws://YOUR_ACCOUNT_ID/us-east-1
```

## Step 3: Build Frontend

```bash
cd frontend
pnpm run build
cd ..
```

## Step 4: Deploy Infrastructure

```bash
# Deploy to dev environment
cdk deploy PricingAppStack-dev --context environment=dev

# Or deploy to production
cdk deploy PricingAppStack-prod --context environment=prod
```

## Step 5: Access the Application

After deployment, CDK will output:
- `WebsiteURL`: The CloudFront URL for your application
- `ApiUrl`: The API Gateway endpoint
- `UserPoolId`: Cognito User Pool ID

Visit the WebsiteURL to access the application.

## Step 6: Enable Bedrock Access

Ensure Claude Haiku 4.5 is enabled in your AWS account:

1. Go to AWS Bedrock console
2. Navigate to Model access
3. Enable `us.anthropic.claude-haiku-4-5-20251001-v1:0`

## Updating the Application

```bash
# Rebuild frontend
cd frontend && pnpm run build && cd ..

# Redeploy
cdk deploy PricingAppStack-dev --context environment=dev
```

## Cleanup

```bash
cdk destroy PricingAppStack-dev --context environment=dev
```

## Troubleshooting

### Lambda Function Errors
```bash
aws logs tail /aws/lambda/PricingAppStack-dev-PricingChatHandler --follow
```

### Frontend Not Loading
- Check CloudFront distribution status
- Verify S3 bucket has files
- Check browser console for errors

### Authentication Issues
- Verify Cognito User Pool configuration
- Check JWT token in browser developer tools
- Ensure API Gateway authorizer is configured correctly
