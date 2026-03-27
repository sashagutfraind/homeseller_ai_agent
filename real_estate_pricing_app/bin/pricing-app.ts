#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import { PricingAppStack } from '../lib/pricing-app-stack';

const app = new cdk.App();

const environment = app.node.tryGetContext('environment') || 'dev';
const account = process.env.CDK_DEFAULT_ACCOUNT;
const region = process.env.CDK_DEFAULT_REGION || 'us-east-1';

new PricingAppStack(app, `PricingAppStack-${environment}`, {
  env: {
    account: account,
    region: region,
  },
  description: `Real Estate Pricing Advisor Stack - ${environment}`,
  tags: {
    Project: 'RealEstatePricingAdvisor',
    Environment: environment,
  },
});

app.synth();
