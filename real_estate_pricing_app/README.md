# Real Estate Pricing Advisor - Full Stack Application

A serverless web application built on AWS that provides AI-powered real estate pricing guidance through Amazon Bedrock. The application features secure user authentication, real-time chat interface, and persistent conversation history.

## Features

- **AI-Powered Pricing Advice**: Interact with Claude Haiku 4.5 via Amazon Bedrock for intelligent pricing recommendations
- **Professional Framework**: Built-in pricing strategy based on Comparative Market Analysis (CMA) principles
- **Secure Authentication**: AWS Cognito-based user registration and login with email verification
- **Conversation History**: Persistent storage and retrieval of pricing consultations with DynamoDB
- **Responsive Design**: Modern React TypeScript frontend optimized for desktop and mobile
- **Serverless Architecture**: Fully serverless deployment using AWS Lambda, API Gateway, and S3
- **Infrastructure as Code**: Complete AWS CDK deployment with TypeScript

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   CloudFront    │────│   S3 Bucket      │    │   Route 53      │
│   (CDN)         │    │   (Frontend)     │    │   (DNS)         │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │
         └───────────────────┐
                             │
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   API Gateway   │────│   Lambda         │────│   Bedrock       │
│   (REST API)    │    │   (Pricing Chat) │    │   (Claude 4.5)  │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │
         │                       │
┌─────────────────┐    ┌──────────────────┐
│   Cognito       │    │   DynamoDB       │
│   (Auth)        │    │   (Storage)      │
└─────────────────┘    └──────────────────┘
```

## Prerequisites

- Node.js (v18 or later)
- pnpm: `npm install -g pnpm` (or use corepack: `corepack enable`)
- AWS CLI (v2 recommended)
- AWS CDK CLI: `pnpm add -g aws-cdk`
- Docker
- AWS Account with Bedrock access (Claude Haiku 4.5 enabled in us-east-1)

## Quick Start

### Option 1: Using Deployment Scripts (Recommended)

```bash
# 1. Configure environment (first time only)
./scripts/configure-environment.sh -e dev -a YOUR_AWS_ACCOUNT_ID

# 2. Deploy everything
./scripts/deploy.sh -e dev
```

### Option 2: Manual Deployment

```bash
# 1. Install dependencies
pnpm install
cd frontend && pnpm install && cd ..

# 2. Bootstrap CDK (first time only)
cdk bootstrap aws://YOUR_ACCOUNT_ID/us-east-1

# 3. Build frontend
cd frontend && pnpm run build && cd ..

# 4. Deploy infrastructure
cdk deploy PricingAppStack-dev --context environment=dev
```

## Available Scripts

- `./scripts/configure-environment.sh` - Configure environment settings
- `./scripts/deploy.sh` - Deploy the complete application
- `./scripts/build-frontend.sh` - Build frontend only
- `./scripts/cleanup.sh` - Destroy the stack and clean up resources

## Pricing Strategy

The application implements professional real estate pricing strategies including:

- **Comparative Market Analysis (CMA)**: Weighted analysis of sold, pending, and active comps
- **Search Bracket Optimization**: Strategic pricing for buyer search filters
- **Market Velocity Adjustments**: Dynamic pricing based on absorption rates
- **FSBO-Specific Guidance**: Tailored advice for For-Sale-By-Owner sellers
- **Price Adjustment Logic**: Data-driven recommendations for listing adjustments

See `PRICE_STRATEGY.md` for detailed methodology.

## License

MIT License
