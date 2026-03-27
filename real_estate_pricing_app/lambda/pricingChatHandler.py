"""
Real Estate Pricing Chat Handler Lambda Function

This Lambda function handles pricing consultation requests from authenticated users,
integrates with Amazon Bedrock Claude Haiku 4.5 for AI-powered pricing advice,
and stores conversation history in DynamoDB.
"""

import json
import boto3
import uuid
import time
import os
import logging
from typing import Dict, Any, Optional
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.resource('dynamodb')
bedrock_runtime = boto3.client('bedrock-runtime')

USER_TABLE_NAME = os.environ['USER_TABLE_NAME']
USER_POOL_ID = os.environ['USER_POOL_ID']
ENVIRONMENT = os.environ['ENVIRONMENT']
BEDROCK_MODEL = "us.anthropic.claude-haiku-4-5-20251001-v1:0"

# Load pricing strategy from environment or use embedded version
PRICE_STRATEGY_TEXT = """[Pricing strategy content embedded here - see PRICE_STRATEGY.md]"""

def build_system_prompt(stage: str, goal: str, seller_type: str) -> str:
    """Build system prompt based on seller profile"""
    stage_label = "setting an initial listing price" if stage == "initial" else "evaluating/adjusting price during an active listing"
    goal_label = "a quick sale" if goal == "quick" else "the highest possible price"
    seller_label = "a For-Sale-By-Owner (FSBO) seller" if seller_type == "fsbo" else "a seller who may be working with or considering an agent"

    return f"""You are an expert real-estate pricing advisor. Your job is to guide the user through {stage_label}.

Seller profile:
- Goal: {goal_label}
- Seller type: {seller_label}

Use the professional pricing framework below as your primary reference. Apply it to whatever comps, market signals, and property details the user shares. Be concise, practical, and specific — give concrete numbers and price ranges whenever possible. Ask follow-up questions to gather missing details (comps, days on market, showings, saves/views, square footage, beds/baths).

=== PRICING STRATEGY REFERENCE ===
{PRICE_STRATEGY_TEXT}
=== END REFERENCE ===

Rules:
- Always recommend a specific price or range, not just vague guidance.
- Respect search bracket thresholds ($25k / $50k increments).
- For FSBO sellers, apply the FSBO-specific advice from the reference.
- If the user pastes raw data (comps, stats), analyse it before advising.
- Keep responses focused — 3–5 short paragraphs maximum unless detail is needed.
"""

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Main Lambda handler for pricing chat requests"""
    try:
        logger.info(f"Received pricing chat request: {json.dumps(event, default=str)}")
        
        user_id = extract_user_id(event)
        if not user_id:
            return create_error_response(401, "Unauthorized: Invalid or missing authentication token")
        
        request_data = parse_request_body(event)
        if not request_data:
            return create_error_response(400, "Bad Request: Invalid JSON in request body")
        
        message = request_data.get('message', '').strip()
        if not message:
            return create_error_response(400, "Bad Request: Message is required and cannot be empty")
        
        if len(message) > 4000:
            return create_error_response(400, "Bad Request: Message exceeds maximum length of 4000 characters")
        
        # Get seller profile from request or session
        stage = request_data.get('stage', 'initial')
        goal = request_data.get('goal', 'quick')
        seller_type = request_data.get('seller_type', 'fsbo')
        conversation_history = request_data.get('conversation_history', [])
        
        sanitized_message = sanitize_input(message)
        request_id = str(uuid.uuid4())
        timestamp = int(time.time() * 1000)
        
        # Call Bedrock with conversation context
        system_prompt = build_system_prompt(stage, goal, seller_type)
        ai_response = call_bedrock_converse(sanitized_message, system_prompt, conversation_history)
        
        if not ai_response:
            return create_error_response(500, "Internal Server Error: Failed to get AI response")
        
        # Store conversation data
        success = store_chat_data(user_id, request_id, timestamp, sanitized_message, ai_response, stage, goal, seller_type)
        if not success:
            logger.error("Failed to store chat data in DynamoDB")
        
        return {
            'statusCode': 200,
            'headers': get_cors_headers(),
            'body': json.dumps({
                'requestId': request_id,
                'message': sanitized_message,
                'response': ai_response,
                'timestamp': timestamp
            })
        }
        
    except Exception as e:
        logger.error(f"Unexpected error in pricing chat handler: {str(e)}", exc_info=True)
        return create_error_response(500, "Internal Server Error: An unexpected error occurred")

def call_bedrock_converse(message: str, system_prompt: str, conversation_history: list) -> Optional[str]:
    """Call Claude via Bedrock Converse API with conversation history"""
    try:
        # Build messages array from conversation history
        messages = []
        for turn in conversation_history:
            messages.append({
                "role": turn.get("role", "user"),
                "content": [{"text": turn.get("content", "")}]
            })
        
        # Add current message
        messages.append({
            "role": "user",
            "content": [{"text": message}]
        })
        
        response = bedrock_runtime.converse(
            modelId=BEDROCK_MODEL,
            system=[{"text": system_prompt}],
            messages=messages,
        )
        
        return response["output"]["message"]["content"][0]["text"]
        
    except ClientError as e:
        logger.error(f"Bedrock ClientError: {e.response['Error']['Code']} - {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Error calling Bedrock: {str(e)}")
        return None

def extract_user_id(event: Dict[str, Any]) -> Optional[str]:
    """Extract user ID from validated JWT token"""
    try:
        request_context = event.get('requestContext', {})
        authorizer = request_context.get('authorizer', {})
        claims = authorizer.get('claims', {})
        user_id = claims.get('sub')
        
        if not user_id:
            logger.warning("No user ID found in JWT claims")
            return None
            
        return user_id
        
    except Exception as e:
        logger.error(f"Error extracting user ID: {str(e)}")
        return None

def parse_request_body(event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Parse and validate JSON request body"""
    try:
        body = event.get('body', '')
        if not body:
            return None
            
        if event.get('isBase64Encoded', False):
            import base64
            body = base64.b64decode(body).decode('utf-8')
        
        return json.loads(body)
        
    except (json.JSONDecodeError, ValueError) as e:
        logger.error(f"Error parsing request body: {str(e)}")
        return None

def sanitize_input(message: str) -> str:
    """Sanitize user input"""
    sanitized = message.strip()
    sanitized = ''.join(char for char in sanitized if ord(char) >= 32 or char in '\n\r\t')
    
    import re
    sanitized = re.sub(r'\s+', ' ', sanitized)
    
    return sanitized

def store_chat_data(user_id: str, request_id: str, timestamp: int, message: str, 
                   response: str, stage: str, goal: str, seller_type: str) -> bool:
    """Store pricing consultation data in DynamoDB"""
    try:
        table = dynamodb.Table(USER_TABLE_NAME)
        
        from datetime import datetime
        created_at = datetime.fromtimestamp(timestamp / 1000).isoformat()
        
        table.put_item(
            Item={
                'userId': user_id,
                'timestamp': timestamp,
                'requestId': request_id,
                'requestText': message,
                'responseText': response,
                'stage': stage,
                'goal': goal,
                'sellerType': seller_type,
                'createdAt': created_at
            }
        )
        
        logger.info(f"Successfully stored pricing chat data for user {user_id}")
        return True
        
    except Exception as e:
        logger.error(f"Error storing chat data: {str(e)}")
        return False

def get_cors_headers() -> Dict[str, str]:
    """Get CORS and security headers"""
    return {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type,Authorization',
        'Access-Control-Allow-Methods': 'POST,OPTIONS',
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'DENY',
        'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
    }

def create_error_response(status_code: int, message: str, request_id: str = None) -> Dict[str, Any]:
    """Create standardized error response"""
    environment = os.environ.get('ENVIRONMENT', 'dev')
    
    if environment == 'prod':
        if status_code >= 500:
            message = "Internal server error occurred"
        elif status_code == 401:
            message = "Authentication required"
    
    logger.warning(f"Returning error response: {status_code} - {message}")
    
    error_response = {
        'error': message,
        'timestamp': int(time.time() * 1000)
    }
    
    if request_id:
        error_response['requestId'] = request_id
    
    return {
        'statusCode': status_code,
        'headers': get_cors_headers(),
        'body': json.dumps(error_response)
    }
