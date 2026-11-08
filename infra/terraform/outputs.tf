output "payment_events_queue_url" {
  value = aws_sqs_queue.payment_events.url
}

output "payment_events_dlq_url" {
  value = aws_sqs_queue.payment_events_dlq.url
}

output "settlement_alerts_topic_arn" {
  value = aws_sns_topic.settlement_alerts.arn
}
