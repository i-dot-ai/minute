resource "aws_sqs_queue" "transcription_queue" {
  name = "${local.name}-transcription-queue"

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.transcription_queue_deadletter.arn
    maxReceiveCount     = 4
  })
}

resource "aws_sqs_queue" "transcription_queue_deadletter" {
  name = "${local.name}-transcription-queue-deadletter"
}

resource "aws_sqs_queue_redrive_allow_policy" "transcription_queue_redrive_allow_policy" {
  queue_url = aws_sqs_queue.transcription_queue_deadletter.id

  redrive_allow_policy = jsonencode({
    redrivePermission = "byQueue",
    sourceQueueArns   = [aws_sqs_queue.transcription_queue.arn]
  })
}
