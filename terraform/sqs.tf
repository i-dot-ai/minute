resource "aws_sqs_queue" "worker_queue_deadletter" {
  name = "${local.name}-worker-queue-deadletter"
}

resource "aws_sqs_queue" "worker_queue" {
  name = "${local.name}-worker-queue"

  # Matches JOB_VISIBILITY_TIMEOUT_SECS the workers run with; the consumer overrides
  # visibility per message anyway, this just keeps the queue default consistent.
  visibility_timeout_seconds = local.JOB_VISIBILITY_TIMEOUT_SECS

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.worker_queue_deadletter.arn
    maxReceiveCount     = 10
  })
}

resource "aws_sqs_queue_redrive_allow_policy" "worker_queue_redrive_allow_policy" {
  queue_url = aws_sqs_queue.worker_queue_deadletter.id

  redrive_allow_policy = jsonencode({
    redrivePermission = "byQueue",
    sourceQueueArns   = [aws_sqs_queue.worker_queue.arn]
  })
}