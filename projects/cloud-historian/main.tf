# Cloud Historian Terraform (simulated customer infra on develop)
resource "aws_ecs_cluster" "app" {
  name = "sitewise-ingestor-app-cluster"
}

resource "aws_sqs_queue" "messages" {
  name                       = "cloud-historian-messages"
  message_retention_seconds  = 1209600
  visibility_timeout_seconds = 120
}
