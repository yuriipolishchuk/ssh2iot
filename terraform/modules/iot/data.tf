data "aws_region" "current" {}
data "aws_caller_identity" "current" {}

data "aws_iot_endpoint" "this" {
  endpoint_type = "iot:Data-ATS"
}
