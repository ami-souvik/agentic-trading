# S3 archive bucket for raw bhavcopy CSVs and full decision/prompt logs.
# Lifecycle rule deletes objects after 90 days to control storage costs.

resource "aws_s3_bucket" "archive" {
  bucket = var.bucket_name

  tags = {
    Name = "${var.name_prefix}-archive"
  }
}

resource "aws_s3_bucket_versioning" "archive" {
  bucket = aws_s3_bucket.archive.id
  versioning_configuration {
    status = "Disabled"  # cost control for Phase 1
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "archive" {
  bucket = aws_s3_bucket.archive.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "archive" {
  bucket                  = aws_s3_bucket.archive.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_lifecycle_configuration" "archive" {
  bucket = aws_s3_bucket.archive.id

  rule {
    id     = "auto-expire"
    status = "Enabled"

    expiration {
      days = var.archive_retention_days
    }

    noncurrent_version_expiration {
      noncurrent_days = 1
    }
  }
}
