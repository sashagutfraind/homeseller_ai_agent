"""
History Handler Lambda Function - retrieves pricing consultation history
"""

import json
import boto3
import os
import logging
import time
from typing import Dict, Any, Optional
from botocore.exceptions import ClientError
from decimal import Decimal

logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.resource('dynamodb')

USER_TABLE_NAME = os.environ['USER_TABLE_NAME']
USER_POOL_ID = os.environ['USER_POOL_ID']
ENVIRONMENT = os.environ['ENVIRONMENT']

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Lambda function to handle user pricing consultation history retrieval"""
    try:
        logger.info(f"Received event: {json.dumps(event, default=str)}")
        
        user_id = extract_user_id(event)
        if not user_id:
            return create_error_response(401, "Unauthorized")
        
        query_params = event.get('queryStringParameters') or {}
        limit = parse_limit(query_params.get('limit'))
        
        history_data = get_user_history(user_id, limit)
        if history_data is None:
            return create_error_response(500, "Failed to retrieve history")
        
        return {
            'statusCode': 200,
            'headers': get_cors_headers(),
            'body': json.dumps(history_data, default=decimal_default)
        }
        
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        return create_error_response(500, "Internal Server Error")

def extract_user_id(event: Dict[str, Any]) -> Optional[str]:
    """Extract user ID from Cognito JWT token"""
    try:
        request_context = event.get('requestContext', {})
        authorizer = request_context.get('authorizer', {})
        claims = authorizer.get('claims', {})
        return claims.get('sub')
    except Exception as e:
        logger.error(f"Error extracting user ID: {str(e)}")
        return None

def parse_limit(limit_str: Optional[str]) -> int:
    """Parse and validate the limit query parameter"""
    try:
        if not limit_str:
            return 20
        limit = int(limit_str)
        return max(1, min(limit, 100))
    except (ValueError, TypeError):
        return 20

def get_user_history(user_id: str, limit: int) -> Optional[Dict[str, Any]]:
    """Retrieve user's pricing consultation history from DynamoDB"""
    try:
        table = dynamodb.Table(USER_TABLE_NAME)
        
        response = table.query(
            KeyConditionExpression=boto3.dynamodb.conditions.Key('userId').eq(user_id),
            ScanIndexForward=False,
            Limit=limit
        )
        
        items = response.get('Items', [])
        processed_items = []
        
        for item in items:
            processed_item = {
                'requestId': item.get('requestId'),
                'timestamp': int(item.get('timestamp', 0)),
                'requestText': item.get('requestText'),
                'responseText': item.get('responseText'),
                'stage': item.get('stage'),
                'goal': item.get('goal'),
                'sellerType': item.get('sellerType'),
                'createdAt': item.get('createdAt')
            }
            processed_items.append(processed_item)
        
        return {
            'items': processed_items,
            'count': len(processed_items)
        }
        
    except Exception as e:
        logger.error(f"Error retrieving history: {str(e)}")
        return None

def decimal_default(obj):
    """JSON serializer for Decimal objects"""
    if isinstance(obj, Decimal):
        return int(obj) if obj % 1 == 0 else float(obj)
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

def get_cors_headers() -> Dict[str, str]:
    """Get CORS and security headers"""
    return {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type,Authorization',
        'Access-Control-Allow-Methods': 'GET,OPTIONS',
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'DENY',
    }

def create_error_response(status_code: int, message: str) -> Dict[str, Any]:
    """Create standardized error response"""
    return {
        'statusCode': status_code,
        'headers': get_cors_headers(),
        'body': json.dumps({
            'error': message,
            'timestamp': int(time.time() * 1000)
        })
    }
