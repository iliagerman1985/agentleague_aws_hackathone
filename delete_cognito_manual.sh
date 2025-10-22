#!/bin/bash

# Manual Cognito deletion script
# Use this if the justfile command is having issues

set -e

echo "🗑️  Manual Cognito Deletion Script"
echo "=================================="

# Load AWS credentials
if [ -f "libs/common/secrets.yaml" ]; then
    echo "Loading AWS credentials from libs/common/secrets.yaml..."
    export AWS_ACCESS_KEY_ID=$(python3 -c "import yaml; data=yaml.safe_load(open('libs/common/secrets.yaml')); print(data['aws']['access_key_id'])")
    export AWS_SECRET_ACCESS_KEY=$(python3 -c "import yaml; data=yaml.safe_load(open('libs/common/secrets.yaml')); print(data['aws']['secret_access_key'])")
    export AWS_DEFAULT_REGION=$(python3 -c "import yaml; data=yaml.safe_load(open('libs/common/secrets.yaml')); print(data['aws']['region'])")
    echo "✓ AWS credentials loaded successfully"
else
    echo "❌ libs/common/secrets.yaml not found"
    exit 1
fi

REGION="us-west-2"

echo ""
echo "📋 Listing all User Pools in region $REGION:"
aws cognito-idp list-user-pools --max-items 60 --region $REGION --output table

echo ""
echo "🗑️  Deleting User Pools..."

# From your screenshot, these are the User Pool IDs:
USER_POOLS=(
    "us-west-2_3Bv1dGmf"
    "us-west-2_4pWF1jbel"
    "us-west-2_jdYTKqmZ"
    "us-west-2_jmvTFgJnA"
)

for POOL_ID in "${USER_POOLS[@]}"; do
    echo ""
    echo "🔍 Processing User Pool: $POOL_ID"
    
    # Check if pool exists
    if aws cognito-idp describe-user-pool --user-pool-id "$POOL_ID" --region $REGION >/dev/null 2>&1; then
        echo "✓ User Pool exists"
        
        # Delete all clients first
        echo "🔍 Finding clients for pool $POOL_ID..."
        CLIENTS=$(aws cognito-idp list-user-pool-clients --user-pool-id "$POOL_ID" --region $REGION --query "UserPoolClients[].ClientId" --output text 2>/dev/null || echo "")
        
        if [ -n "$CLIENTS" ] && [ "$CLIENTS" != "None" ]; then
            echo "🗑️  Deleting clients..."
            for CLIENT_ID in $CLIENTS; do
                echo "  Deleting client: $CLIENT_ID"
                aws cognito-idp delete-user-pool-client \
                    --user-pool-id "$POOL_ID" \
                    --client-id "$CLIENT_ID" \
                    --region $REGION
            done
            echo "✓ All clients deleted"
        else
            echo "ℹ️  No clients found"
        fi
        
        # Delete the user pool
        echo "🗑️  Deleting User Pool $POOL_ID..."
        aws cognito-idp delete-user-pool \
            --user-pool-id "$POOL_ID" \
            --region $REGION
        echo "✓ User Pool deleted successfully"
    else
        echo "ℹ️  User Pool $POOL_ID not found (may already be deleted)"
    fi
done

echo ""
echo "🎉 Manual deletion complete!"
echo ""
echo "📋 Remaining User Pools:"
aws cognito-idp list-user-pools --max-items 60 --region $REGION --output table

echo ""
echo "📝 Next steps:"
echo "1. Verify all unwanted pools are deleted"
echo "2. Run 'just create_cognito_dev' to create a fresh development pool"
echo "3. Update your secrets.yaml with the new pool configuration"
