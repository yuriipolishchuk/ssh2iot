resource "aws_s3_bucket" "terraform_state" {
  bucket = var.bucket

  acl = "private"

  versioning {
    enabled = true
  }

  server_side_encryption_configuration {
    rule {
      apply_server_side_encryption_by_default {
        sse_algorithm = "AES256"
      }
    }
  }

  force_destroy = var.force_destroy
}

resource "aws_dynamodb_table" "tf_lock" {
  name = "tf_lock"

  billing_mode   = "PROVISIONED"
  read_capacity  = 1
  write_capacity = 1

  hash_key = "LockID"

  attribute {
    name = "LockID"
    type = "S"
  }
}
