# ============================================================================
# AURORA SERVERLESS V2 RDS CLUSTER
# ============================================================================

# DB Subnet Group for Aurora
resource "aws_db_subnet_group" "aurora" {
  name       = "${var.project_name}-${var.environment}-aurora-subnet-group"
  subnet_ids = aws_subnet.private[*].id

  tags = {
    Name        = "${var.project_name}-${var.environment}-aurora-subnet-group"
    Environment = var.environment
  }
}

# Security Group for Aurora RDS
resource "aws_security_group" "aurora" {
  name        = "${var.project_name}-${var.environment}-aurora-sg"
  description = "Security group for Aurora PostgreSQL Serverless v2"
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "PostgreSQL from backend"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.backend.id]
  }

  egress {
    description = "Allow all outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "${var.project_name}-${var.environment}-aurora-sg"
    Environment = var.environment
  }
}

# Random password for Aurora master user
resource "random_password" "aurora_master_password" {
  length  = 32
  special = true
  # Exclude characters that might cause issues in connection strings
  override_special = "!#$%&*()-_=+[]{}<>:?"
}

# Store Aurora credentials in Secrets Manager
resource "aws_secretsmanager_secret" "aurora_credentials" {
  name        = "${var.project_name}-${var.environment}-aurora-credentials"
  description = "Aurora PostgreSQL master credentials for ${var.environment}"

  tags = {
    Name        = "${var.project_name}-${var.environment}-aurora-credentials"
    Environment = var.environment
  }
}

resource "aws_secretsmanager_secret_version" "aurora_credentials" {
  secret_id = aws_secretsmanager_secret.aurora_credentials.id
  secret_string = jsonencode({
    username = var.aurora_master_username
    password = random_password.aurora_master_password.result
    engine   = "postgres"
    host     = aws_rds_cluster.aurora.endpoint
    port     = 5432
    dbname   = var.aurora_database_name
  })
}

# Aurora RDS Cluster (Serverless v2)
resource "aws_rds_cluster" "aurora" {
  cluster_identifier      = "${var.project_name}-${var.environment}-aurora-cluster"
  engine                  = "aurora-postgresql"
  engine_mode             = "provisioned"
  engine_version          = var.aurora_engine_version
  database_name           = var.aurora_database_name
  master_username         = var.aurora_master_username
  master_password         = random_password.aurora_master_password.result
  db_subnet_group_name    = aws_db_subnet_group.aurora.name
  vpc_security_group_ids  = [aws_security_group.aurora.id]
  
  # Serverless v2 scaling configuration
  serverlessv2_scaling_configuration {
    min_capacity = var.aurora_min_capacity
    max_capacity = var.aurora_max_capacity
  }

  # Backup configuration
  backup_retention_period = var.aurora_backup_retention_period
  preferred_backup_window = "03:00-04:00"
  
  # Maintenance window
  preferred_maintenance_window = "sun:04:00-sun:05:00"
  
  # Enable encryption
  storage_encrypted = true
  
  # Skip final snapshot for hackathon environment (change for production)
  skip_final_snapshot = var.environment == "hackathon" ? true : false
  final_snapshot_identifier = var.environment == "hackathon" ? null : "${var.project_name}-${var.environment}-final-snapshot-${formatdate("YYYY-MM-DD-hhmm", timestamp())}"
  
  # Enable deletion protection for production
  deletion_protection = var.environment == "production" ? true : false
  
  # Enable CloudWatch logs
  enabled_cloudwatch_logs_exports = ["postgresql"]
  
  # Apply changes immediately for hackathon
  apply_immediately = var.environment == "hackathon" ? true : false

  tags = {
    Name        = "${var.project_name}-${var.environment}-aurora-cluster"
    Environment = var.environment
  }
}

# Aurora Serverless v2 Instance (Writer)
resource "aws_rds_cluster_instance" "aurora_writer" {
  identifier              = "${var.project_name}-${var.environment}-aurora-writer"
  cluster_identifier      = aws_rds_cluster.aurora.id
  instance_class          = "db.serverless"
  engine                  = aws_rds_cluster.aurora.engine
  engine_version          = aws_rds_cluster.aurora.engine_version
  
  # Performance Insights
  performance_insights_enabled = true
  performance_insights_retention_period = 7
  
  # Monitoring
  monitoring_interval = 60
  monitoring_role_arn = aws_iam_role.rds_monitoring.arn
  
  # Apply changes immediately for hackathon
  apply_immediately = var.environment == "hackathon" ? true : false

  tags = {
    Name        = "${var.project_name}-${var.environment}-aurora-writer"
    Environment = var.environment
    Role        = "writer"
  }
}

# Optional: Aurora Serverless v2 Instance (Reader) - uncomment if needed
# resource "aws_rds_cluster_instance" "aurora_reader" {
#   identifier              = "${var.project_name}-${var.environment}-aurora-reader"
#   cluster_identifier      = aws_rds_cluster.aurora.id
#   instance_class          = "db.serverless"
#   engine                  = aws_rds_cluster.aurora.engine
#   engine_version          = aws_rds_cluster.aurora.engine_version
#   
#   # Performance Insights
#   performance_insights_enabled = true
#   performance_insights_retention_period = 7
#   
#   # Monitoring
#   monitoring_interval = 60
#   monitoring_role_arn = aws_iam_role.rds_monitoring.arn
#   
#   # Apply changes immediately for hackathon
#   apply_immediately = var.environment == "hackathon" ? true : false
#
#   tags = {
#     Name        = "${var.project_name}-${var.environment}-aurora-reader"
#     Environment = var.environment
#     Role        = "reader"
#   }
# }

# IAM Role for RDS Enhanced Monitoring
resource "aws_iam_role" "rds_monitoring" {
  name = "${var.project_name}-${var.environment}-rds-monitoring"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "monitoring.rds.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name        = "${var.project_name}-${var.environment}-rds-monitoring"
    Environment = var.environment
  }
}

resource "aws_iam_role_policy_attachment" "rds_monitoring" {
  role       = aws_iam_role.rds_monitoring.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonRDSEnhancedMonitoringRole"
}

# CloudWatch Log Group for Aurora
resource "aws_cloudwatch_log_group" "aurora" {
  name              = "/aws/rds/cluster/${aws_rds_cluster.aurora.cluster_identifier}/postgresql"
  retention_in_days = 7

  tags = {
    Name        = "${var.project_name}-${var.environment}-aurora-logs"
    Environment = var.environment
  }
}

