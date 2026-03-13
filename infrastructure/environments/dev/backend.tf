terraform {
  backend "s3" {
    bucket         = "robops-terraform-state-dev"
    key            = "dev/terraform.tfstate"
    region         = "ap-northeast-1"
    dynamodb_table = "robops-terraform-locks"
    encrypt        = true
  }
}
