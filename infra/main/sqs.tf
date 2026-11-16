resource "aws_sqs_queue" "work_dlq" {
  name                      = "${var.project}-work-dlq"
  message_retention_seconds = 1209600 # 14 days, the maximum: time to investigate
  sqs_managed_sse_enabled   = true
}

resource "aws_sqs_queue" "work" {
  name = "${var.project}-work"
  # AWS guidance for Lambda event sources: at least 6x the function timeout,
  # so a message isn't redelivered while a slow invocation is still running.
  visibility_timeout_seconds = var.worker_timeout_seconds * 6
  message_retention_seconds  = 345600 # 4 days
  receive_wait_time_seconds  = 20     # long polling: fewer empty receives
  sqs_managed_sse_enabled    = true

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.work_dlq.arn
    maxReceiveCount     = 3
  })
}

# Separate resource to avoid a dependency cycle between the two queues.
resource "aws_sqs_queue_redrive_allow_policy" "work_dlq" {
  queue_url = aws_sqs_queue.work_dlq.id
  redrive_allow_policy = jsonencode({
    redrivePermission = "byQueue"
    sourceQueueArns   = [aws_sqs_queue.work.arn]
  })
}
