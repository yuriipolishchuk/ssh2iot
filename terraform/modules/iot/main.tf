resource "aws_iot_thing" "this" {
  for_each = toset(var.iot_things)
  name     = each.value
}

#TODO: in production use separate certs for each IoT thing
resource "aws_iot_certificate" "this" {
  active = true
}

#TODO: set proper permissions
resource "aws_iot_policy" "this" {
  name = "PubSubToAnyTopic"

  policy = <<-EOF
    {
      "Version": "2012-10-17",
      "Statement": [
        {
          "Action": [
            "iot:*"
          ],
          "Effect": "Allow",
          "Resource": "*"
        }
      ]
    }
  EOF
}

resource "aws_iot_policy_attachment" "this" {
  policy = aws_iot_policy.this.name
  target = aws_iot_certificate.this.arn
}

resource "aws_iot_thing_principal_attachment" "this" {
  for_each = aws_iot_thing.this

  principal = aws_iot_certificate.this.arn
  thing     = each.value.name
}
