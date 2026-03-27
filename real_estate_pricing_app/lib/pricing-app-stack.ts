import * as cdk from 'aws-cdk-lib';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as iam from 'aws-cdk-lib/aws-iam';
import { Construct } from 'constructs';
import { FrontendConstruct } from './constructs/frontend-construct';
import { AuthConstruct } from './constructs/auth-construct';
import { ApiConstruct } from './constructs/api-construct';
import { StorageConstruct } from './constructs/storage-construct';

export class PricingAppStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    const environment = this.node.tryGetContext('environment') || 'dev';
    const environments = this.node.tryGetContext('environments') || {};
    const envConfig = environments[environment] || {};
    const domainName = envConfig.domainName || this.node.tryGetContext('domainName');

    // Storage layer - DynamoDB table for pricing consultations
    const storage = new StorageConstruct(this, 'Storage', {
      environment,
    });

    // Authentication layer - Cognito User Pool and Identity Pool
    const auth = new AuthConstruct(this, 'Auth', {
      environment,
    });

    // API layer - API Gateway and Lambda functions
    const api = new ApiConstruct(this, 'Api', {
      userPool: auth.userPool,
      userTable: storage.userTable,
      environment,
      envConfig,
    });

    // Frontend layer - S3 bucket and CloudFront distribution
    const frontend = new FrontendConstruct(this, 'Frontend', {
      userPoolId: auth.userPool.userPoolId,
      userPoolClientId: auth.userPoolClient.userPoolClientId,
      identityPoolId: auth.identityPool.ref,
      apiUrl: api.apiGateway.url,
      domainName,
      environment,
    });

    // CloudFormation Outputs
    new cdk.CfnOutput(this, 'WebsiteURL', {
      value: domainName ? `https://${domainName}` : `https://${frontend.distribution.distributionDomainName}`,
      description: 'Website URL',
      exportName: `${id}-WebsiteURL`,
    });

    new cdk.CfnOutput(this, 'CloudFrontURL', {
      value: `https://${frontend.distribution.distributionDomainName}`,
      description: 'CloudFront Distribution URL',
      exportName: `${id}-CloudFrontURL`,
    });

    new cdk.CfnOutput(this, 'UserPoolId', {
      value: auth.userPool.userPoolId,
      description: 'Cognito User Pool ID',
      exportName: `${id}-UserPoolId`,
    });

    new cdk.CfnOutput(this, 'UserPoolClientId', {
      value: auth.userPoolClient.userPoolClientId,
      description: 'Cognito User Pool Client ID',
      exportName: `${id}-UserPoolClientId`,
    });

    new cdk.CfnOutput(this, 'IdentityPoolId', {
      value: auth.identityPool.ref,
      description: 'Cognito Identity Pool ID',
      exportName: `${id}-IdentityPoolId`,
    });

    new cdk.CfnOutput(this, 'ApiUrl', {
      value: api.apiGateway.url,
      description: 'API Gateway URL',
      exportName: `${id}-ApiUrl`,
    });

    new cdk.CfnOutput(this, 'Region', {
      value: this.region,
      description: 'AWS Region',
      exportName: `${id}-Region`,
    });

    new cdk.CfnOutput(this, 'Environment', {
      value: environment,
      description: 'Deployment Environment',
      exportName: `${id}-Environment`,
    });
  }
}
