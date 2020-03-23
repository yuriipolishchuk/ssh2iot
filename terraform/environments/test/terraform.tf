terraform {
  required_version = "= 0.12.24"

  backend "s3" {
    bucket         = "terraform-state.iot-test.yuriipolischuk.net"
    key            = "aws/test/eu-west-1"
    region         = "eu-west-1"
    dynamodb_table = "tf_lock"
    encrypt        = true
  }
}
