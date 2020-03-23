output "this" {
  sensitive = true

  value = {
    iot_things  = aws_iot_thing.this
    endpoint    = data.aws_iot_endpoint.this.endpoint_address
    certificate = aws_iot_certificate.this
  }
}
