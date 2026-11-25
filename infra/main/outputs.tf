output "api_url" {
  value = aws_apigatewayv2_stage.default.invoke_url
}

output "work_queue_url" {
  value = aws_sqs_queue.work.url
}

output "work_dlq_url" {
  value = aws_sqs_queue.work_dlq.url
}

output "table_name" {
  value = aws_dynamodb_table.main.name
}

output "raw_bucket" {
  value = aws_s3_bucket.raw.bucket
}
