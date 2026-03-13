output "schedule_group_name" {
  value = aws_scheduler_schedule_group.main.name
}

output "scheduler_role_arn" {
  value = aws_iam_role.scheduler.arn
}
