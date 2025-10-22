#!/bin/bash

# Simple monitoring script for AWS deployment
# This script checks the health of all services and reports status

set -e

# Configuration
PROJECT_NAME="agentleague"
AWS_REGION="us-east-1"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to log with colors and timestamp
log_info() {
    echo -e "${GREEN}[$(date '+%H:%M:%S')] INFO:${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[$(date '+%H:%M:%S')] WARN:${NC} $1"
}

log_error() {
    echo -e "${RED}[$(date '+%H:%M:%S')] ERROR:${NC} $1"
}

log_header() {
    echo -e "${BLUE}[$(date '+%H:%M:%S')] === $1 ===${NC}"
}

# Function to check HTTP endpoint
check_endpoint() {
    local url=$1
    local name=$2
    local timeout=${3:-10}
    
    if curl -f -s --max-time $timeout "$url" > /dev/null 2>&1; then
        log_info "✅ $name is healthy"
        return 0
    else
        log_error "❌ $name is not responding"
        return 1
    fi
}

# Function to get EC2 instance information
get_instance_info() {
    log_header "EC2 Instance Information"
    
    local instance_info=$(aws ec2 describe-instances \
        --filters "Name=tag:Name,Values=${PROJECT_NAME}-*instance*" "Name=instance-state-name,Values=running" \
        --query 'Reservations[0].Instances[0].[InstanceId,PublicIpAddress,PrivateIpAddress,InstanceType,State.Name]' \
        --output text --region $AWS_REGION 2>/dev/null)
    
    if [ "$instance_info" != "None" ] && [ -n "$instance_info" ]; then
        echo "$instance_info" | while read -r instance_id public_ip private_ip instance_type state; do
            log_info "Instance ID: $instance_id"
            log_info "Public IP: $public_ip"
            log_info "Private IP: $private_ip"
            log_info "Instance Type: $instance_type"
            log_info "State: $state"
            
            # Export for use in other functions
            echo "$public_ip" > /tmp/instance_ip
        done
    else
        log_error "No running EC2 instance found"
        return 1
    fi
}

# Function to check ALB status
check_alb_status() {
    log_header "Application Load Balancer Status"
    
    local alb_info=$(aws elbv2 describe-load-balancers \
        --names "${PROJECT_NAME}-alb" \
        --query 'LoadBalancers[0].[DNSName,State.Code]' \
        --output text --region $AWS_REGION 2>/dev/null)
    
    if [ "$alb_info" != "None" ] && [ -n "$alb_info" ]; then
        echo "$alb_info" | while read -r dns_name state; do
            log_info "ALB DNS: $dns_name"
            log_info "ALB State: $state"
            
            if [ "$state" = "active" ]; then
                log_info "✅ ALB is active"
            else
                log_warn "⚠️  ALB is not active: $state"
            fi
        done
    else
        log_error "ALB not found"
        return 1
    fi
}

# Function to check target group health
check_target_groups() {
    log_header "Target Group Health"
    
    # Get target groups
    local tg_arns=$(aws elbv2 describe-target-groups \
        --names "${PROJECT_NAME}-backend-tg" "${PROJECT_NAME}-frontend-tg" \
        --query 'TargetGroups[].TargetGroupArn' \
        --output text --region $AWS_REGION 2>/dev/null)
    
    if [ -n "$tg_arns" ]; then
        for tg_arn in $tg_arns; do
            local tg_name=$(aws elbv2 describe-target-groups \
                --target-group-arns "$tg_arn" \
                --query 'TargetGroups[0].TargetGroupName' \
                --output text --region $AWS_REGION)
            
            log_info "Checking target group: $tg_name"
            
            local health_status=$(aws elbv2 describe-target-health \
                --target-group-arn "$tg_arn" \
                --query 'TargetHealthDescriptions[0].TargetHealth.State' \
                --output text --region $AWS_REGION 2>/dev/null)
            
            if [ "$health_status" = "healthy" ]; then
                log_info "✅ $tg_name targets are healthy"
            else
                log_warn "⚠️  $tg_name targets are $health_status"
            fi
        done
    else
        log_error "No target groups found"
    fi
}

# Function to check service endpoints
check_service_endpoints() {
    log_header "Service Health Checks"
    
    if [ ! -f /tmp/instance_ip ]; then
        log_error "Instance IP not available"
        return 1
    fi
    
    local instance_ip=$(cat /tmp/instance_ip)
    
    # Check backend health
    check_endpoint "http://$instance_ip:9998/health" "Backend API"
    
    # Check frontend
    check_endpoint "http://$instance_ip:5888/" "Frontend" 5
    
    # Check detailed backend health
    log_info "Getting detailed backend health info..."
    local backend_health=$(curl -s "http://$instance_ip:9998/health" 2>/dev/null || echo "Failed to get health info")
    echo "Backend health details: $backend_health"
}

# Function to check Docker containers on EC2
check_docker_containers() {
    log_header "Docker Container Status"
    
    if [ ! -f /tmp/instance_ip ]; then
        log_error "Instance IP not available"
        return 1
    fi
    
    local instance_ip=$(cat /tmp/instance_ip)
    
    log_info "Note: To check Docker containers, SSH into the instance:"
    log_info "ssh -i ~/.ssh/your-key.pem ec2-user@$instance_ip"
    log_info "sudo docker-compose -f /opt/app/docker-compose.aws.yml ps"
}

# Function to check CloudWatch logs
check_cloudwatch_logs() {
    log_header "CloudWatch Logs"
    
    local log_groups=(
        "/aws/ec2/${PROJECT_NAME}"
        "/aws/ec2/${PROJECT_NAME}/backend"
        "/aws/ec2/${PROJECT_NAME}/frontend"
        "/aws/ec2/${PROJECT_NAME}/postgres"
    )
    
    for log_group in "${log_groups[@]}"; do
        local latest_event=$(aws logs describe-log-streams \
            --log-group-name "$log_group" \
            --order-by LastEventTime \
            --descending \
            --max-items 1 \
            --query 'logStreams[0].lastEventTime' \
            --output text --region $AWS_REGION 2>/dev/null)
        
        if [ "$latest_event" != "None" ] && [ -n "$latest_event" ]; then
            local last_log_time=$(date -d "@$((latest_event / 1000))" '+%Y-%m-%d %H:%M:%S' 2>/dev/null || echo "Unknown")
            log_info "✅ $log_group - Last log: $last_log_time"
        else
            log_warn "⚠️  $log_group - No recent logs or log group doesn't exist"
        fi
    done
}

# Function to show cost estimate
show_cost_estimate() {
    log_header "Estimated Monthly Cost"
    
    log_info "💰 Estimated AWS costs for dev environment:"
    log_info "   • EC2 t3.medium spot instance: ~$15-25/month"
    log_info "   • Application Load Balancer: ~$16/month"
    log_info "   • CloudWatch Logs (7 days retention): ~$1-3/month"
    log_info "   • ECR storage: ~$1-2/month"
    log_info "   • Data transfer: ~$1-5/month"
    log_info "   • Total estimated: $34-51/month"
    log_info ""
    log_info "💡 Cost optimization tips:"
    log_info "   • Spot instances save ~70% vs On-Demand"
    log_info "   • Short log retention (7 days) reduces costs"
    log_info "   • Containerized DB avoids RDS costs"
}

# Main monitoring function
main() {
    log_header "AgentLeague AWS Deployment Monitor"
    log_info "Starting health check at $(date)"
    echo
    
    # Check if AWS CLI is configured
    if ! aws sts get-caller-identity > /dev/null 2>&1; then
        log_error "AWS CLI not configured or credentials invalid"
        exit 1
    fi
    
    # Run all checks
    get_instance_info || log_error "Failed to get instance info"
    echo
    
    check_alb_status || log_error "Failed to check ALB status"
    echo
    
    check_target_groups || log_error "Failed to check target groups"
    echo
    
    check_service_endpoints || log_error "Failed to check service endpoints"
    echo
    
    check_docker_containers
    echo
    
    check_cloudwatch_logs || log_error "Failed to check CloudWatch logs"
    echo
    
    show_cost_estimate
    echo
    
    log_info "Health check completed at $(date)"
    
    # Cleanup
    rm -f /tmp/instance_ip
}

# Run main function
main "$@"
