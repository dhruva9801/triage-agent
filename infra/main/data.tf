# One table for every entity (postings, quota counters), keyed by the owner's
# Cognito sub. On-demand billing: pay per request, nothing while idle.
resource "aws_dynamodb_table" "main" {
  name         = var.project
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "PK"
  range_key    = "SK"

  attribute {
    name = "PK"
    type = "S"
  }
  attribute {
    name = "SK"
    type = "S"
  }

  # Daily quota counters delete themselves once they are no longer needed.
  ttl {
    attribute_name = "expires_at"
    enabled        = true
  }

  # Restore to any second in the last 35 days. Costs cents at this size.
  point_in_time_recovery {
    enabled = true
  }
}

# Raw posting text, kept so extraction can be re-run after a prompt change
# without fetching the posting again.
resource "aws_s3_bucket" "raw" {
  bucket = "${var.project}-raw-${local.account_id}"
}

resource "aws_s3_bucket_public_access_block" "raw" {
  bucket                  = aws_s3_bucket.raw.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

data "aws_iam_policy_document" "raw_tls_only" {
  statement {
    sid       = "DenyInsecureTransport"
    effect    = "Deny"
    actions   = ["s3:*"]
    resources = [aws_s3_bucket.raw.arn, "${aws_s3_bucket.raw.arn}/*"]
    principals {
      type        = "*"
      identifiers = ["*"]
    }
    condition {
      test     = "Bool"
      variable = "aws:SecureTransport"
      values   = ["false"]
    }
  }
}

resource "aws_s3_bucket_policy" "raw" {
  bucket = aws_s3_bucket.raw.id
  policy = data.aws_iam_policy_document.raw_tls_only.json
}
