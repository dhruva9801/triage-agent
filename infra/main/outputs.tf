output "api_url" {
  value = aws_apigatewayv2_stage.default.invoke_url
}

output "work_queue_url" {
  value = aws_sqs_queue.work.url
}

output "work_dlq_url" {
  value = aws_sqs_queue.work_dlq.url
}
