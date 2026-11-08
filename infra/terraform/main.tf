terraform {
  required_version = ">= 1.9.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

resource "aws_sqs_queue" "payment_events_dlq" {
  name                      = "${var.name_prefix}-payment-events-dlq"
  message_retention_seconds = 1209600
  sqs_managed_sse_enabled   = true
}

resource "aws_sqs_queue" "payment_events" {
  name                      = "${var.name_prefix}-payment-events"
  message_retention_seconds = 345600
  visibility_timeout_seconds = 60

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.payment_events_dlq.arn
    maxReceiveCount     = 5
  })

  sqs_managed_sse_enabled = true
}

resource "aws_sns_topic" "settlement_alerts" {
  name = "${var.name_prefix}-settlement-alerts"
}

resource "aws_cloudwatch_metric_alarm" "parked_settlements" {
  alarm_name          = "${var.name_prefix}-parked-settlements"
  alarm_description   = "Settlements parked because an authorization has not arrived."
  namespace           = "SettlementGuard"
  metric_name         = "ParkedSettlements"
  statistic           = "Maximum"
  period              = 60
  evaluation_periods  = 2
  threshold           = var.parked_settlement_threshold
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"

  alarm_actions = [aws_sns_topic.settlement_alerts.arn]
}

resource "aws_cloudwatch_metric_alarm" "reconciliation_breaks" {
  alarm_name          = "${var.name_prefix}-reconciliation-breaks"
  alarm_description   = "Reconciliation breaks exceeded the operating threshold."
  namespace           = "SettlementGuard"
  metric_name         = "ReconciliationBreaks"
  statistic           = "Sum"
  period              = 300
  evaluation_periods  = 1
  threshold           = var.reconciliation_break_threshold
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"

  alarm_actions = [aws_sns_topic.settlement_alerts.arn]
}
