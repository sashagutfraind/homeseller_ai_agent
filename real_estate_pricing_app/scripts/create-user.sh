#!/bin/bash

# Script to create a new user in the Cognito User Pool
# Usage: ./scripts/create-user.sh your-email@example.com

set -e

if [ -z "$1" ]; then
  echo "Usage: $0 <email>"
  echo "Example: $0 user@example.com"
  exit 1
fi

EMAIL=$1
USER_POOL_ID="us-east-1_23RTFoRtW"
TEMP_PASSWORD="TempPassword123!"

echo "Creating user: $EMAIL"
echo "User Pool ID: $USER_POOL_ID"
echo ""

aws cognito-idp admin-create-user \
  --user-pool-id "$USER_POOL_ID" \
  --username "$EMAIL" \
  --user-attributes Name=email,Value="$EMAIL" Name=email_verified,Value=true \
  --temporary-password "$TEMP_PASSWORD" \
  --message-action SUPPRESS \
  --region us-east-1

echo ""
echo "✅ User created successfully!"
echo ""
echo "Login credentials:"
echo "  Email: $EMAIL"
echo "  Temporary Password: $TEMP_PASSWORD"
echo ""
echo "The user will be prompted to change their password on first login."
echo ""
echo "Access the application at: https://dafhc9dch4ru6.cloudfront.net"
