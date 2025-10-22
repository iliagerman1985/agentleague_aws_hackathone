terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    bucket  = "agentleague-dev-tf-state"
    key     = "dev/terraform.tfstate"
    region  = "us-east-1"
    encrypt = true
  }
}

provider "aws" {
  region = var.aws_region
}

# Data sources
data "aws_availability_zones" "available" {
  state = "available"
}

data "aws_caller_identity" "current" {}

# Using specific Ubuntu ARM AMI
# data "aws_ami" "ubuntu_arm" {
#   most_recent = true
#   owners      = ["099720109477"] # Canonical
#
#   filter {
#     name   = "name"
#     values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-arm64-server-*"]
#   }
#
#   filter {
#     name   = "virtualization-type"
#     values = ["hvm"]
#   }
# }

# VPC
resource "aws_vpc" "main" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name        = "${var.project_name}-vpc"
    Environment = var.environment
  }
}

# Internet Gateway
resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id

  tags = {
    Name        = "${var.project_name}-igw"
    Environment = var.environment
  }
}

# Public Subnets
resource "aws_subnet" "public" {
  count = 2

  vpc_id                  = aws_vpc.main.id
  cidr_block              = "10.0.${count.index + 1}.0/24"
  availability_zone       = data.aws_availability_zones.available.names[count.index]
  map_public_ip_on_launch = true

  tags = {
    Name        = "${var.project_name}-public-subnet-${count.index + 1}"
    Environment = var.environment
  }
}

# Route Table
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }

  tags = {
    Name        = "${var.project_name}-public-rt"
    Environment = var.environment
  }
}

# Route Table Associations
resource "aws_route_table_association" "public" {
  count = length(aws_subnet.public)

  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

# Security Groups
resource "aws_security_group" "alb" {
  name_prefix = "${var.project_name}-alb-"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "${var.project_name}-alb-sg"
    Environment = var.environment
  }
}

resource "aws_security_group" "ec2" {
  name_prefix = "${var.project_name}-ec2-"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port       = 80
    to_port         = 80
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  ingress {
    from_port       = 5888
    to_port         = 5888
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  ingress {
    from_port       = 9998
    to_port         = 9998
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]  # Restrict this to your IP in production
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "${var.project_name}-ec2-sg"
    Environment = var.environment
  }
}

# ECR Repository
resource "aws_ecr_repository" "backend" {
  name                 = "${var.project_name}-backend"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = {
    Environment = var.environment
  }
}

resource "aws_ecr_repository" "frontend" {
  name                 = "${var.project_name}-frontend"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = {
    Environment = var.environment
  }
}

resource "aws_ecr_repository" "agentcore" {
  name                 = "${var.project_name}-agentcore"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = {
    Environment = var.environment
  }
}

# ECR Lifecycle Policies
resource "aws_ecr_lifecycle_policy" "backend" {
  repository = aws_ecr_repository.backend.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Keep last 10 images"
        selection = {
          tagStatus     = "tagged"
          tagPrefixList = ["v"]
          countType     = "imageCountMoreThan"
          countNumber   = 10
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
}

resource "aws_ecr_lifecycle_policy" "frontend" {
  repository = aws_ecr_repository.frontend.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Keep last 10 images"
        selection = {
          tagStatus     = "tagged"
          tagPrefixList = ["v"]
          countType     = "imageCountMoreThan"
          countNumber   = 10
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
}

resource "aws_ecr_lifecycle_policy" "agentcore" {
  repository = aws_ecr_repository.agentcore.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Keep last 10 images"
        selection = {
          tagStatus     = "tagged"
          tagPrefixList = ["v"]
          countType     = "imageCountMoreThan"
          countNumber   = 10
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
}

# IAM Role for EC2 Instance
resource "aws_iam_role" "ec2_role" {
  name = "${var.project_name}-ec2-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Environment = var.environment
  }
}

# IAM Policy for EC2 Instance
resource "aws_iam_role_policy" "ec2_policy" {
  name = "${var.project_name}-ec2-policy"
  role = aws_iam_role.ec2_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ecr:GetAuthorizationToken",
          "ecr:BatchCheckLayerAvailability",
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Resource = "arn:aws:secretsmanager:${var.aws_region}:*:secret:dev_secret*"
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "logs:DescribeLogStreams"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "ssm:GetParameter",
          "ssm:GetParameters",
          "ssm:GetParametersByPath"
        ]
        Resource = "arn:aws:ssm:${var.aws_region}:*:parameter/${var.project_name}/*"
      },
      {
        Effect = "Allow"
        Action = [
          "sqs:SendMessage",
          "sqs:ReceiveMessage",
          "sqs:DeleteMessage",
          "sqs:GetQueueAttributes",
          "sqs:GetQueueUrl"
        ]
        Resource = [
          aws_sqs_queue.game_turn.arn,
          aws_sqs_queue.game_turn_dead_letter.arn,
          aws_sqs_queue.game_analysis.arn,
          aws_sqs_queue.game_analysis_dead_letter.arn
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "ec2:DescribeVolumes",
          "ec2:AttachVolume",
          "ec2:DetachVolume",
          "ec2:DescribeInstances"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "bedrock-agentcore:CreateAgentRuntime",
          "bedrock-agentcore:GetAgentRuntime",
          "bedrock-agentcore:UpdateAgentRuntime",
          "bedrock-agentcore:DeleteAgentRuntime",
          "bedrock-agentcore:InvokeAgentRuntime",
          "bedrock-agentcore:ListAgentRuntimes"
        ]
        Resource = "*"
      }
    ]
  })
}

# IAM Instance Profile
resource "aws_iam_instance_profile" "ec2_profile" {
  name = "${var.project_name}-ec2-profile"
  role = aws_iam_role.ec2_role.name
}

# Secrets Manager Secret - managed by scripts/create-dev-secret.sh
# The secret 'dev_secret' is created and managed by the create-dev-secret.sh script


# CloudWatch Log Groups
resource "aws_cloudwatch_log_group" "app_logs" {
  name              = "/aws/ec2/${var.project_name}"
  retention_in_days = 7  # Keep logs for 7 days to save costs

  tags = {
    Environment = var.environment
  }
}

resource "aws_cloudwatch_log_group" "backend_logs" {
  name              = "/aws/ec2/${var.project_name}/backend"
  retention_in_days = 7

  tags = {
    Environment = var.environment
  }
}

resource "aws_cloudwatch_log_group" "frontend_logs" {
  name              = "/aws/ec2/${var.project_name}/frontend"
  retention_in_days = 7

  tags = {
    Environment = var.environment
  }
}

resource "aws_cloudwatch_log_group" "postgres_logs" {
  name              = "/aws/ec2/${var.project_name}/postgres"
  retention_in_days = 7

  tags = {
    Environment = var.environment
  }
}

resource "aws_cloudwatch_log_group" "agentcore_logs" {
  name              = "/aws/bedrock-agentcore/${var.project_name}"
  retention_in_days = 7

  tags = {
    Environment = var.environment
  }
}

# SQS Queues for AgentLeague
# Dead Letter Queue (must be created first)
resource "aws_sqs_queue" "process_message_dead_letter" {
  name                      = "process-message-dead-letter-queue"
  message_retention_seconds = 1209600  # 14 days

  tags = {
    Name        = "${var.project_name}-process-message-dlq"
    Environment = var.environment
  }
}

# Main process message queue with DLQ
resource "aws_sqs_queue" "process_message" {
  name                      = "process-message-queue"
  visibility_timeout_seconds = 300
  message_retention_seconds = 1209600  # 14 days

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.process_message_dead_letter.arn
    maxReceiveCount     = 10
  })

  tags = {
    Name        = "${var.project_name}-process-message-queue"
    Environment = var.environment
  }
}

# Billing events queue
resource "aws_sqs_queue" "billing_events" {
  name                      = "billing-events-queue"
  visibility_timeout_seconds = 300
  message_retention_seconds = 1209600  # 14 days

  tags = {
    Name        = "${var.project_name}-billing-events-queue"
    Environment = var.environment
  }
}

# Webhooks queue
resource "aws_sqs_queue" "webhooks" {
  name                      = "webhooks-queue"
  visibility_timeout_seconds = 300
  message_retention_seconds = 1209600  # 14 days

  tags = {
    Name        = "${var.project_name}-webhooks-queue"
    Environment = var.environment
  }
}

# Game turn queue with DLQ
resource "aws_sqs_queue" "game_turn_dead_letter" {
  name                      = "${var.project_name}-game-turn-dlq-${var.environment}"
  message_retention_seconds = 1209600  # 14 days

  tags = {
    Name        = "${var.project_name}-game-turn-dlq-${var.environment}"
    Environment = var.environment
  }
}

resource "aws_sqs_queue" "game_turn" {
  name                       = "${var.project_name}-game-turn-queue-${var.environment}"
  visibility_timeout_seconds = 300  # 5 minutes for game turn processing
  message_retention_seconds  = 1209600  # 14 days

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.game_turn_dead_letter.arn
    maxReceiveCount     = 3  # Retry failed turns up to 3 times
  })

  tags = {
    Name        = "${var.project_name}-game-turn-queue-${var.environment}"
    Environment = var.environment
  }
}

# Game analysis queue with DLQ
resource "aws_sqs_queue" "game_analysis_dead_letter" {
  name                      = "${var.project_name}-game-analysis-dlq-${var.environment}"
  message_retention_seconds = 1209600  # 14 days

  tags = {
    Name        = "${var.project_name}-game-analysis-dlq-${var.environment}"
    Environment = var.environment
  }
}

resource "aws_sqs_queue" "game_analysis" {
  name                       = "${var.project_name}-game-analysis-queue-${var.environment}"
  visibility_timeout_seconds = 300  # 5 minutes for analysis processing
  message_retention_seconds  = 1209600  # 14 days

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.game_analysis_dead_letter.arn
    maxReceiveCount     = 3  # Retry failed analysis up to 3 times
  })

  tags = {
    Name        = "${var.project_name}-game-analysis-queue-${var.environment}"
    Environment = var.environment
  }
}

# Application Load Balancer
resource "aws_lb" "main" {
  name               = "${var.project_name}-alb"
  internal           = false
  idle_timeout       = 300
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = aws_subnet.public[*].id

  enable_deletion_protection = false  # Set to true for production

  tags = {
    Environment = var.environment
  }
}

# ALB Target Group for Frontend
resource "aws_lb_target_group" "frontend" {
  name     = "${var.project_name}-frontend-tg"
  port     = 5888
  protocol = "HTTP"
  vpc_id   = aws_vpc.main.id

  health_check {
    enabled             = true
    healthy_threshold   = 2
    interval            = 30
    matcher             = "200"
    path                = "/"
    port                = "traffic-port"
    protocol            = "HTTP"
    timeout             = 5
    unhealthy_threshold = 2
  }

  tags = {
    Environment = var.environment
  }
}

# ALB Target Group for Backend
resource "aws_lb_target_group" "backend" {
  name     = "${var.project_name}-backend-tg"
  port     = 9998
  protocol = "HTTP"
  vpc_id   = aws_vpc.main.id

  health_check {
    enabled             = true
    healthy_threshold   = 2
    interval            = 30
    matcher             = "200"
    path                = "/health"
    port                = "traffic-port"
    protocol            = "HTTP"
    timeout             = 5
    unhealthy_threshold = 2
  }

  tags = {
    Environment = var.environment
  }
}

# ALB Listener (HTTPS)
resource "aws_lb_listener" "https" {
  load_balancer_arn = aws_lb.main.arn
  port              = "443"
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS-1-2-2017-01"
  certificate_arn   = var.certificate_arn

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.frontend.arn
  }
}

# ALB Listener (HTTP - redirect to HTTPS)
resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.main.arn
  port              = "80"
  protocol          = "HTTP"

  default_action {
    type = "redirect"

    redirect {
      port        = "443"
      protocol    = "HTTPS"
      status_code = "HTTP_301"
    }
  }
}

# ALB Listener Rule for Backend API
resource "aws_lb_listener_rule" "backend_api" {
  listener_arn = aws_lb_listener.https.arn
  priority     = 100

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.backend.arn
  }

  condition {
    path_pattern {
      values = ["/api/*", "/docs", "/redoc", "/openapi.json"]
    }
  }
}

# Launch Template for EC2 Instance
resource "aws_launch_template" "app" {
  name_prefix   = "${var.project_name}-"
  image_id      = var.ami_id
  instance_type = var.instance_type
  key_name      = var.key_pair_name

  vpc_security_group_ids = [aws_security_group.ec2.id]

  # Increase root volume size to handle Docker images and logs
  block_device_mappings {
    device_name = "/dev/sda1"
    ebs {
      volume_size = 30  # GB (increased from default ~8GB)
      volume_type = "gp3"
      delete_on_termination = true
      encrypted = true
    }
  }

  iam_instance_profile {
    name = aws_iam_instance_profile.ec2_profile.name
  }

  user_data = base64encode(templatefile("${path.module}/user_data.sh", {
    project_name           = var.project_name
    aws_region             = var.aws_region
    ecr_backend_repo       = aws_ecr_repository.backend.repository_url
    ecr_frontend_repo      = aws_ecr_repository.frontend.repository_url
    ecr_agentcore_repo     = aws_ecr_repository.agentcore.repository_url
    secrets_manager_name   = "dev_secret"
    log_group_app          = aws_cloudwatch_log_group.app_logs.name
    log_group_backend      = aws_cloudwatch_log_group.backend_logs.name
    log_group_frontend     = aws_cloudwatch_log_group.frontend_logs.name
    log_group_postgres     = aws_cloudwatch_log_group.postgres_logs.name
    log_group_agentcore    = aws_cloudwatch_log_group.agentcore_logs.name
    environment            = var.environment
  }))

  tag_specifications {
    resource_type = "instance"
    tags = {
      Name        = "${var.project_name}-instance"
      Environment = var.environment
    }
  }

  tags = {
    Environment = var.environment
  }
}
# EBS volume for PostgreSQL data (single-AZ, used by ASG instance)
resource "aws_ebs_volume" "pg_data" {
  availability_zone = aws_subnet.public[0].availability_zone
  size              = var.pg_data_volume_size
  type              = "gp3"
  encrypted         = true

  tags = {
    Name        = "${var.project_name}-pg-data"
    Environment = var.environment
  }
}


# EC2 Instance (Spot or On-Demand)
resource "aws_instance" "app" {
  count = var.enable_spot_instance ? 0 : 1

  launch_template {
    id      = aws_launch_template.app.id
    version = "$Latest"

  }

  subnet_id = aws_subnet.public[0].id

  tags = {
    Name        = "${var.project_name}-instance"
    Environment = var.environment
  }
}

# Auto Scaling Group for Spot Instances (desired capacity = 1)
resource "aws_autoscaling_group" "app" {
  count                = var.enable_spot_instance ? 1 : 0
  name                 = "${var.project_name}-asg"
  min_size             = 1
  desired_capacity     = 1
  max_size             = 1

  vpc_zone_identifier        = [aws_subnet.public[0].id]
  health_check_type          = "ELB"
  health_check_grace_period  = 300
  target_group_arns          = [aws_lb_target_group.frontend.arn, aws_lb_target_group.backend.arn]
  capacity_rebalance         = true

  mixed_instances_policy {
    launch_template {
      launch_template_specification {
        launch_template_id = aws_launch_template.app.id
        version            = "$Latest"
      }
    }

    instances_distribution {
      on_demand_base_capacity                  = 0
      on_demand_percentage_above_base_capacity = 0
      spot_allocation_strategy                 = "capacity-optimized"
      spot_max_price                           = var.spot_price
    }
  }

  tag {
    key                 = "Name"
    value               = "${var.project_name}-instance"
    propagate_at_launch = true
  }

  tag {
    key                 = "Environment"
    value               = var.environment
    propagate_at_launch = true
  }
}



# Target Group Attachments for On-Demand Instance
resource "aws_lb_target_group_attachment" "frontend_ondemand" {
  count = var.enable_spot_instance ? 0 : 1

  target_group_arn = aws_lb_target_group.frontend.arn
  target_id        = aws_instance.app[0].id
  port             = 5888
}

resource "aws_lb_target_group_attachment" "backend_ondemand" {
  count = var.enable_spot_instance ? 0 : 1

  target_group_arn = aws_lb_target_group.backend.arn
  target_id        = aws_instance.app[0].id
  port             = 9998
}


