import * as cdk from 'aws-cdk-lib';
import * as apigateway from 'aws-cdk-lib/aws-apigateway';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as cognito from 'aws-cdk-lib/aws-cognito';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import * as logs from 'aws-cdk-lib/aws-logs';
import { Construct } from 'constructs';
import * as path from 'path';

export interface ApiConstructProps {
  userPool: cognito.UserPool;
  userTable: dynamodb.Table;
  environment: string;
  envConfig?: any;
}

export class ApiConstruct extends Construct {
  public readonly apiGateway: apigateway.RestApi;
  public readonly pricingChatHandler: lambda.Function;
  public readonly historyHandler: lambda.Function;

  constructor(scope: Construct, id: string, props: ApiConstructProps) {
    super(scope, id);

    const lambdaRole = new iam.Role(this, 'LambdaExecutionRole', {
      assumedBy: new iam.ServicePrincipal('lambda.amazonaws.com'),
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName('service-role/AWSLambdaBasicExecutionRole'),
      ],
    });

    props.userTable.grantReadWriteData(lambdaRole);

    lambdaRole.addToPolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: ['bedrock:InvokeModel'],
      resources: [
        `arn:aws:bedrock:${cdk.Stack.of(this).region}::foundation-model/us.anthropic.claude-haiku-4-5-20251001-v1:0`,
      ],
    }));

    this.pricingChatHandler = new lambda.Function(this, 'PricingChatHandler', {
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'pricingChatHandler.lambda_handler',
      code: lambda.Code.fromAsset(path.join(__dirname, '../../lambda')),
      role: lambdaRole,
      environment: {
        USER_TABLE_NAME: props.userTable.tableName,
        USER_POOL_ID: props.userPool.userPoolId,
        ENVIRONMENT: props.environment,
      },
      timeout: cdk.Duration.seconds(30),
      memorySize: 256,
      logRetention: logs.RetentionDays.ONE_WEEK,
    });

    this.historyHandler = new lambda.Function(this, 'HistoryHandler', {
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'historyHandler.lambda_handler',
      code: lambda.Code.fromAsset(path.join(__dirname, '../../lambda')),
      role: lambdaRole,
      environment: {
        USER_TABLE_NAME: props.userTable.tableName,
        USER_POOL_ID: props.userPool.userPoolId,
        ENVIRONMENT: props.environment,
      },
      timeout: cdk.Duration.seconds(15),
      memorySize: 128,
      logRetention: logs.RetentionDays.ONE_WEEK,
    });

    const cognitoAuthorizer = new apigateway.CognitoUserPoolsAuthorizer(this, 'CognitoAuthorizer', {
      cognitoUserPools: [props.userPool],
      identitySource: 'method.request.header.Authorization',
    });

    this.apiGateway = new apigateway.RestApi(this, 'Api', {
      restApiName: `Pricing Advisor API ${props.environment}`,
      deployOptions: {
        stageName: props.environment,
        throttlingRateLimit: 50,
        throttlingBurstLimit: 100,
        metricsEnabled: true,
      },
      defaultCorsPreflightOptions: {
        allowOrigins: ['*'],
        allowMethods: ['GET', 'POST', 'OPTIONS'],
        allowHeaders: ['Content-Type', 'Authorization'],
        allowCredentials: true,
      },
    });

    const apiV1 = this.apiGateway.root.addResource('api').addResource('v1');

    const chatResource = apiV1.addResource('chat');
    chatResource.addMethod('POST', new apigateway.LambdaIntegration(this.pricingChatHandler), {
      authorizer: cognitoAuthorizer,
      authorizationType: apigateway.AuthorizationType.COGNITO,
    });

    const historyResource = apiV1.addResource('history');
    historyResource.addMethod('GET', new apigateway.LambdaIntegration(this.historyHandler), {
      authorizer: cognitoAuthorizer,
      authorizationType: apigateway.AuthorizationType.COGNITO,
    });
  }
}
