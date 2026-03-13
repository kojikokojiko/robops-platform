output "ecr_repository_url" {
  value = aws_ecr_repository.emulator.repository_url
}

output "ecr_repository_name" {
  value = aws_ecr_repository.emulator.name
}

output "ecs_cluster_name" {
  value = aws_ecs_cluster.emulators.name
}

output "ecs_cluster_arn" {
  value = aws_ecs_cluster.emulators.arn
}
