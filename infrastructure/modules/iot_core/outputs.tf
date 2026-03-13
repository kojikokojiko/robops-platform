output "thing_group_name" {
  value = aws_iot_thing_group.robots.name
}

output "policy_name" {
  value = aws_iot_policy.robot.name
}

output "robot_certificate_arns" {
  value = { for k, v in aws_iot_certificate.robot : k => v.arn }
}

output "robot_secret_arns" {
  value = { for k, v in aws_secretsmanager_secret.robot_cert : k => v.arn }
}

output "robot_secret_names" {
  value = { for k, v in aws_secretsmanager_secret.robot_cert : k => v.name }
}
