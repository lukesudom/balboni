resource "aws_ecr_repository" "webhook_receiver" {
  name = "webhook-receiver"
}

resource "aws_ecr_repository" "repo_scanner" {
  name = "repo-scanner"
}

resource "aws_sqs_queue" "repo_scan_queue" {
  name                      = "repo-scan-queue"
  delay_seconds             = 0
  max_message_size          = 2048
  message_retention_seconds = 86400
  receive_wait_time_seconds = 10
}

resource "aws_lambda_function" "webhook_receiver" {
  function_name = "webhook-receiver"
  role          = aws_iam_role.lambda_role.arn
  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.webhook_receiver.repository_url}:${var.image_tag}"

  environment {
    variables = {
      SQS_QUEUE_URL = aws_sqs_queue.repo_scan_queue.url
      DISCORD_WEBHOOK_URL = var.discord_webhook_url
    }
  }

  depends_on = [null_resource.docker_builds]

  lifecycle {
    replace_triggered_by = [
      null_resource.docker_builds
    ]
  }
}

resource "aws_lambda_function" "repo_scanner" {
  function_name = "repo-scanner"
  role          = aws_iam_role.scanner_lambda_role.arn
  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.repo_scanner.repository_url}:${var.image_tag}"

  timeout       = 900
  memory_size   = 1024

  environment {
    variables = {
      GIT_USERNAME = var.git_username
      GIT_TOKEN    = var.git_token
      DISCORD_WEBHOOK_URL = var.discord_webhook_url
    }
  }

  depends_on = [null_resource.docker_builds]

  lifecycle {
    replace_triggered_by = [
      null_resource.docker_builds
    ]
  }
}


resource "aws_iam_role" "lambda_role" {
  name = "webhook-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_basic_execution" {
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
  role       = aws_iam_role.lambda_role.name
}

resource "aws_iam_role_policy_attachment" "scanner_lambda_basic_execution" {
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
  role       = aws_iam_role.scanner_lambda_role.name
}

resource "aws_iam_role_policy" "lambda_sqs_policy" {
  name = "lambda-sqs-policy"
  role = aws_iam_role.lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "sqs:SendMessage"
        ]
        Resource = aws_sqs_queue.repo_scan_queue.arn
      }
    ]
  })
}

resource "aws_iam_role" "scanner_lambda_role" {
  name = "scanner-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy" "scanner_lambda_policy" {
  name = "scanner-lambda-policy"
  role = aws_iam_role.scanner_lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "sqs:ReceiveMessage",
          "sqs:DeleteMessage",
          "sqs:GetQueueAttributes"
        ]
        Resource = aws_sqs_queue.repo_scan_queue.arn
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:*"
      }
    ]
  })
}

resource "aws_lambda_event_source_mapping" "sqs_trigger" {
  event_source_arn = aws_sqs_queue.repo_scan_queue.arn
  function_name    = aws_lambda_function.repo_scanner.arn
  batch_size       = 1
}


resource "aws_apigatewayv2_api" "webhook_api" {
  name          = "webhook-api"
  protocol_type = "HTTP"
}

resource "aws_apigatewayv2_integration" "lambda_integration" {
  api_id           = aws_apigatewayv2_api.webhook_api.id
  integration_type = "AWS_PROXY"
  integration_uri  = aws_lambda_function.webhook_receiver.invoke_arn
  integration_method = "POST"
}

resource "aws_apigatewayv2_route" "webhook_route" {
  api_id    = aws_apigatewayv2_api.webhook_api.id
  route_key = "POST /webhook"
  target    = "integrations/${aws_apigatewayv2_integration.lambda_integration.id}"
}

resource "aws_apigatewayv2_stage" "webhook_stage" {
  api_id      = aws_apigatewayv2_api.webhook_api.id
  name        = "$default"
  auto_deploy = true
}

# Lambda Permissions
resource "aws_lambda_permission" "api_gw" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.webhook_receiver.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.webhook_api.execution_arn}/*/*"
}

resource "null_resource" "docker_builds" {
  triggers = {
    webhook_receiver_hash = filemd5("${path.module}/../webhook_receiver/Dockerfile")
    repo_scanner_hash     = filemd5("${path.module}/../repo_scanner/Dockerfile")
    webhook_receiver_code = filemd5("${path.module}/../webhook_receiver/lambda_function.py")
    repo_scanner_code     = filemd5("${path.module}/../repo_scanner/lambda_function.py")
    image_tag             = var.image_tag
  }

  provisioner "local-exec" {
    command = <<-EOT
      # Delete old images
      aws ecr batch-delete-image --repository-name webhook-receiver --image-ids imageTag=${var.image_tag} --region ${var.region} || true
      aws ecr batch-delete-image --repository-name repo-scanner --image-ids imageTag=${var.image_tag} --region ${var.region} || true

      # Build and push new images
      ./entrypoint.sh ${aws_ecr_repository.webhook_receiver.repository_url} ${aws_ecr_repository.repo_scanner.repository_url} ${var.region} ${var.image_tag}
    EOT

    working_dir = path.module == "." ? ".." : dirname(path.module)
  }

  depends_on = [
    aws_ecr_repository.webhook_receiver,
    aws_ecr_repository.repo_scanner
  ]
}

output "api_endpoint" {
  value = aws_apigatewayv2_stage.webhook_stage.invoke_url
}