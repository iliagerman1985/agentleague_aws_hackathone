#!/bin/bash

# Script to initialize Terraform backend with S3 and DynamoDB
# This script sets up the S3 bucket and DynamoDB table for Terraform state management

set -e

# Configuration
PROJECT_NAME="agentleague"
ENVIRONMENT="dev"
AWS_REGION="us-east-1"
BUCKET_NAME="agentleague-dev-tf-state"
DYNAMODB_TABLE="agentleague-dev-tf-locks"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to log with colors
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_header() {
    echo -e "${BLUE}=== $1 ===${NC}"
}

# Check if AWS CLI is configured
check_aws_cli() {
    log_header "Checking AWS CLI Configuration"
    
    if ! command -v aws &> /dev/null; then
        log_error "AWS CLI is not installed. Please install it first."
        exit 1
    fi
    
    if ! aws sts get-caller-identity > /dev/null 2>&1; then
        log_error "AWS credentials not configured or invalid"
        log_info "Please run 'aws configure' to set up your credentials"
        exit 1
    fi
    
    local account_id=$(aws sts get-caller-identity --query Account --output text)
    local current_region=$(aws configure get region)
    
    log_info "✅ AWS CLI configured"
    log_info "Account ID: $account_id"
    log_info "Current region: $current_region"
    
    if [ "$current_region" != "$AWS_REGION" ]; then
        log_warn "Current AWS region ($current_region) differs from target region ($AWS_REGION)"
        log_info "This script will use region: $AWS_REGION"
    fi
}

# Check if S3 bucket exists
check_s3_bucket() {
    log_header "Checking S3 Bucket"
    
    if aws s3api head-bucket --bucket "$BUCKET_NAME" --region "$AWS_REGION" 2>/dev/null; then
        log_info "✅ S3 bucket '$BUCKET_NAME' already exists"
        
        # Check if versioning is enabled
        local versioning=$(aws s3api get-bucket-versioning --bucket "$BUCKET_NAME" --region "$AWS_REGION" --query Status --output text 2>/dev/null || echo "None")
        if [ "$versioning" = "Enabled" ]; then
            log_info "✅ Bucket versioning is enabled"
        else
            log_warn "⚠️  Bucket versioning is not enabled. Enabling now..."
            aws s3api put-bucket-versioning --bucket "$BUCKET_NAME" --versioning-configuration Status=Enabled --region "$AWS_REGION"
            log_info "✅ Bucket versioning enabled"
        fi
        
        # Check if encryption is enabled
        if aws s3api get-bucket-encryption --bucket "$BUCKET_NAME" --region "$AWS_REGION" >/dev/null 2>&1; then
            log_info "✅ Bucket encryption is enabled"
        else
            log_warn "⚠️  Bucket encryption is not enabled. Enabling now..."
            aws s3api put-bucket-encryption --bucket "$BUCKET_NAME" --region "$AWS_REGION" \
                --server-side-encryption-configuration '{
                    "Rules": [
                        {
                            "ApplyServerSideEncryptionByDefault": {
                                "SSEAlgorithm": "AES256"
                            }
                        }
                    ]
                }'
            log_info "✅ Bucket encryption enabled"
        fi
    else
        log_error "❌ S3 bucket '$BUCKET_NAME' does not exist"
        log_info "Please create the bucket first or run this script with --create-bucket flag"
        exit 1
    fi
}

# Check if DynamoDB table exists
check_dynamodb_table() {
    log_header "Checking DynamoDB Table"
    
    if aws dynamodb describe-table --table-name "$DYNAMODB_TABLE" --region "$AWS_REGION" >/dev/null 2>&1; then
        log_info "✅ DynamoDB table '$DYNAMODB_TABLE' already exists"
    else
        log_warn "⚠️  DynamoDB table '$DYNAMODB_TABLE' does not exist. Creating now..."
        
        aws dynamodb create-table \
            --table-name "$DYNAMODB_TABLE" \
            --attribute-definitions AttributeName=LockID,AttributeType=S \
            --key-schema AttributeName=LockID,KeyType=HASH \
            --billing-mode PAY_PER_REQUEST \
            --region "$AWS_REGION" \
            --tags Key=Name,Value="${PROJECT_NAME}-terraform-locks" Key=Environment,Value="$ENVIRONMENT" \
            >/dev/null
        
        log_info "⏳ Waiting for table to be created..."
        aws dynamodb wait table-exists --table-name "$DYNAMODB_TABLE" --region "$AWS_REGION"
        log_info "✅ DynamoDB table created successfully"
    fi
}

# Initialize Terraform backend
init_terraform() {
    log_header "Initializing Terraform Backend"
    
    if [ ! -f "terraform/main.tf" ]; then
        log_error "terraform/main.tf not found. Please run this script from the project root."
        exit 1
    fi
    
    cd terraform
    
    # Remove any existing .terraform directory to force re-initialization
    if [ -d ".terraform" ]; then
        log_info "Removing existing .terraform directory..."
        rm -rf .terraform
    fi
    
    log_info "Running terraform init..."
    if terraform init; then
        log_info "✅ Terraform backend initialized successfully"
    else
        log_error "❌ Terraform initialization failed"
        exit 1
    fi
    
    cd ..
}

# Verify backend configuration
verify_backend() {
    log_header "Verifying Backend Configuration"
    
    cd terraform
    
    # Check if state is stored in S3
    if terraform state list >/dev/null 2>&1; then
        log_info "✅ Terraform state is accessible"
        
        # Show backend configuration
        log_info "Backend configuration:"
        log_info "  Bucket: $BUCKET_NAME"
        log_info "  Key: dev/terraform.tfstate"
        log_info "  Region: $AWS_REGION"
        log_info "  DynamoDB Table: $DYNAMODB_TABLE"
    else
        log_warn "⚠️  Terraform state is empty (this is normal for new deployments)"
    fi
    
    cd ..
}

# Main function
main() {
    log_header "Terraform Backend Initialization"
    log_info "Setting up S3 backend for Terraform state management"
    echo
    
    check_aws_cli
    echo
    
    check_s3_bucket
    echo
    
    check_dynamodb_table
    echo
    
    init_terraform
    echo
    
    verify_backend
    echo
    
    log_info "🎉 Terraform backend setup completed successfully!"
    echo
    log_info "Next steps:"
    log_info "1. Configure terraform.tfvars with your settings"
    log_info "2. Run 'terraform plan' to review changes"
    log_info "3. Run 'terraform apply' to deploy infrastructure"
    echo
    log_info "Your Terraform state will be stored in:"
    log_info "  S3: s3://$BUCKET_NAME/dev/terraform.tfstate"
    log_info "  DynamoDB: $DYNAMODB_TABLE (for state locking)"
}

# Handle command line arguments
if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    echo "Usage: $0 [--help]"
    echo
    echo "This script initializes the Terraform backend with S3 and DynamoDB."
    echo "It assumes the S3 bucket '$BUCKET_NAME' already exists."
    echo
    echo "Prerequisites:"
    echo "  - AWS CLI configured with appropriate permissions"
    echo "  - S3 bucket '$BUCKET_NAME' exists in region '$AWS_REGION'"
    echo
    exit 0
fi

# Run main function
main "$@"
