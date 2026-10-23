terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
  default_tags {
    tags = {
      Project     = "ClaimSense-AI"
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  }
}

# -----------------------------------------------------------------------------
# NETWORKING (VPC & SUBNETS)
# -----------------------------------------------------------------------------
data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

# -----------------------------------------------------------------------------
# SECURITY GROUPS
# -----------------------------------------------------------------------------
resource "aws_security_group" "alb_sg" {
  name        = "${var.app_name}-alb-sg"
  description = "Allow inbound HTTP/HTTPS traffic to ALB"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    description = "HTTP"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "HTTPS"
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
}

resource "aws_security_group" "ecs_sg" {
  name        = "${var.app_name}-ecs-sg"
  description = "Allow inbound traffic from ALB only"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    description     = "Inbound from ALB"
    from_port       = var.container_port
    to_port         = var.container_port
    protocol        = "tcp"
    security_groups = [aws_security_group.alb_sg.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# -----------------------------------------------------------------------------
# ECR REPOSITORY
# -----------------------------------------------------------------------------
resource "aws_ecr_repository" "app_repo" {
  name                 = var.app_name
  image_tag_mutability = "IMMUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }
}

resource "aws_ecr_lifecycle_policy" "repo_policy" {
  repository = aws_ecr_repository.app_repo.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Keep last 10 production images"
        selection = {
          tagStatus   = "any"
          countType   = "sinceImagePushed"
          countUnit   = "days"
          countNumber = 30
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
}

# -----------------------------------------------------------------------------
# CLOUDWATCH LOGS & RETENTION
# -----------------------------------------------------------------------------
resource "aws_cloudwatch_log_group" "ecs_logs" {
  name              = "/ecs/${var.app_name}"
  retention_in_days = 90
}

# -----------------------------------------------------------------------------
# IAM ROLES (LEAST PRIVILEGE)
# -----------------------------------------------------------------------------
resource "aws_iam_role" "ecs_task_execution_role" {
  name = "${var.app_name}-execution-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action    = "sts:AssumeRole"
        Effect    = "Allow"
        Principal = { Service = "ecs-tasks.amazonaws.com" }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "ecs_task_execution_policy" {
  role       = aws_iam_role.ecs_task_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role" "ecs_task_role" {
  name = "${var.app_name}-task-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action    = "sts:AssumeRole"
        Effect    = "Allow"
        Principal = { Service = "ecs-tasks.amazonaws.com" }
      }
    ]
  })
}

resource "aws_iam_role_policy" "cloudwatch_metrics_policy" {
  name = "${var.app_name}-metrics-policy"
  role = aws_iam_role.ecs_task_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "cloudwatch:PutMetricData",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "*"
      }
    ]
  })
}

# -----------------------------------------------------------------------------
# ECS CLUSTER & TASK DEFINITION
# -----------------------------------------------------------------------------
resource "aws_ecs_cluster" "main" {
  name = "${var.app_name}-cluster"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}

resource "aws_ecs_task_definition" "app" {
  family                   = var.app_name
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = tostring(var.fargate_cpu)
  memory                   = tostring(var.fargate_memory)
  execution_role_arn       = aws_iam_role.ecs_task_execution_role.arn
  task_role_arn            = aws_iam_role.ecs_task_role.arn

  container_definitions = jsonencode([
    {
      name      = var.app_name
      image     = "${aws_ecr_repository.app_repo.repository_url}:latest"
      essential = true
      portMappings = [
        {
          containerPort = var.container_port
          hostPort      = var.container_port
          protocol      = "tcp"
        }
      ]
      environment = [
        { name = "ENVIRONMENT", value = var.environment },
        { name = "PORT", value = tostring(var.container_port) },
        { name = "LOG_LEVEL", value = "INFO" }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.ecs_logs.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "ecs"
        }
      }
    }
  ])
}

# -----------------------------------------------------------------------------
# APPLICATION LOAD BALANCER
# -----------------------------------------------------------------------------
resource "aws_lb" "main" {
  name               = "${var.app_name}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb_sg.id]
  subnets            = data.aws_subnets.default.ids
}

resource "aws_lb_target_group" "app" {
  name        = "${var.app_name}-tg"
  port        = var.container_port
  protocol    = "HTTP"
  vpc_id      = data.aws_vpc.default.id
  target_type = "ip"

  health_check {
    enabled             = true
    path                = "/health"
    protocol            = "HTTP"
    matcher             = "200"
    interval            = 30
    timeout             = 5
    healthy_threshold   = 2
    unhealthy_threshold = 3
  }
}

resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.main.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.app.arn
  }
}

# -----------------------------------------------------------------------------
# ECS SERVICE (FARGATE)
# -----------------------------------------------------------------------------
resource "aws_ecs_service" "app" {
  name            = "${var.app_name}-service"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.app.arn
  desired_count   = 2
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = data.aws_subnets.default.ids
    security_groups  = [aws_security_group.ecs_sg.id]
    assign_public_ip = true
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.app.arn
    container_name   = var.app_name
    container_port   = var.container_port
  }

  depends_on = [aws_lb_listener.http]
}

# -----------------------------------------------------------------------------
# CLOUDWATCH DASHBOARD & OPERATIONAL ALARMS
# -----------------------------------------------------------------------------
resource "aws_cloudwatch_dashboard" "main" {
  dashboard_name = "ClaimSense-Operational-Metrics"

  dashboard_body = jsonencode({
    widgets = [
      {
        type   = "metric"
        x      = 0
        y      = 0
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["ClaimSenseAI", "PipelineLatency", "Metric", "p95", { stat = "p95", period = 60, label = "p95 Adjudication Latency (ms)" }],
            ["...", { stat = "Average", period = 60, label = "Avg Latency (ms)" }]
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "Adjudication Pipeline Latency (Target: p95 ≤ 60s)"
          annotations = {
            horizontal = [
              { value = 60000, label = "Target SLA (60s)", color = "#e07a5f" }
            ]
          }
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 0
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["ClaimSenseAI", "AdjudicationCalls", "Outcome", "Approve", { stat = "Sum", period = 300 }],
            ["...", "Flag", { stat = "Sum", period = 300 }],
            ["...", "Route", { stat = "Sum", period = 300 }],
            ["...", "Deny", { stat = "Sum", period = 300 }]
          ]
          view    = "timeSeries"
          stacked = true
          region  = var.aws_region
          title   = "Adjudication Call Volume by Decision Outcome"
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 6
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["ClaimSenseAI", "ErrorRate", { stat = "Average", period = 60, label = "Error Rate (%)" }]
          ]
          view    = "timeSeries"
          region  = var.aws_region
          title   = "Pipeline Error Rate (%)"
          annotations = {
            horizontal = [
              { value = 5.0, label = "Alarm Threshold (5%)", color = "#d62828" }
            ]
          }
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 6
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["ClaimSenseAI", "AccessRefusals", { stat = "Sum", period = 300, label = "Entitlement Refusals (403)" }]
          ]
          view    = "timeSeries"
          region  = var.aws_region
          title   = "Security Trust Boundary: Access Refusals"
        }
      }
    ]
  })
}

resource "aws_cloudwatch_metric_alarm" "high_latency" {
  alarm_name          = "ClaimSense-HighLatencyAlarm"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "PipelineLatency"
  namespace           = "ClaimSenseAI"
  period              = 60
  extended_statistic  = "p95"
  threshold           = 60000
  alarm_description   = "Triggers when p95 adjudication latency exceeds 60 seconds over 2 consecutive evaluation periods."
}

resource "aws_cloudwatch_metric_alarm" "high_error_rate" {
  alarm_name          = "ClaimSense-HighErrorRateAlarm"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "ErrorRate"
  namespace           = "ClaimSenseAI"
  period              = 60
  statistic           = "Average"
  threshold           = 5.0
  alarm_description   = "Triggers when the pipeline error rate exceeds 5% over 2 consecutive minutes."
}
