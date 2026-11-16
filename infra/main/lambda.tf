resource "aws_lambda_function" "api" {
  function_name = "${var.project}-api"
  role          = aws_iam_role.api.arn
  package_type  = "Image"
  image_uri     = var.api_image_uri
  architectures = ["x86_64"]
  memory_size   = 512
  # API Gateway HTTP APIs cut off at 30 s. The API only enqueues work, so it
  # should never come close.
  timeout = 15

  environment {
    variables = {
      TRIAGE_ENV = "aws"
    }
  }

  logging_config {
    log_format = "JSON"
    log_group  = aws_cloudwatch_log_group.api.name
  }
}

resource "aws_lambda_function" "worker" {
  function_name = "${var.project}-worker"
  role          = aws_iam_role.worker.arn
  package_type  = "Image"
  image_uri     = var.worker_image_uri
  architectures = ["x86_64"]
  memory_size   = 512
  timeout       = var.worker_timeout_seconds

  environment {
    variables = {
      TRIAGE_ENV              = "aws"
      POWERTOOLS_SERVICE_NAME = "triage-worker"
    }
  }

  logging_config {
    log_format = "JSON"
    log_group  = aws_cloudwatch_log_group.worker.name
  }
}

resource "aws_lambda_event_source_mapping" "work" {
  event_source_arn = aws_sqs_queue.work.arn
  function_name    = aws_lambda_function.worker.arn
  batch_size       = 1
  # The handler reports per-message failures (batchItemFailures); without
  # this setting Lambda ignores that and retries the whole batch.
  function_response_types = ["ReportBatchItemFailures"]

  # The cost fuse. Use this, not reserved concurrency: reserved concurrency
  # below the poller's demand causes throttled messages to burn receive
  # attempts and land in the DLQ without ever running.
  scaling_config {
    maximum_concurrency = 2
  }

  # The worker must be allowed to read the queue before the mapping exists.
  depends_on = [aws_iam_role_policy.worker]
}
