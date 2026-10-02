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

resource "aws_sqs_queue" "llm_queue" {
  name = "${local.name}-llm-queue"

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.llm_queue_deadletter.arn
    maxReceiveCount     = 4
  })
}

resource "aws_sqs_queue" "llm_queue_deadletter" {
  name = "${local.name}-llm-queue-deadletter"
}

resource "aws_sqs_queue_redrive_allow_policy" "llm_queue_redrive_allow_policy" {
  queue_url = aws_sqs_queue.llm_queue_deadletter.id

  redrive_allow_policy = jsonencode({
    redrivePermission = "byQueue",
    sourceQueueArns   = [aws_sqs_queue.llm_queue.arn]
  })
}

resource "aws_sqs_queue" "audio_queue" {
  name = "${local.name}-audio-queue"

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.audio_queue_deadletter.arn
    maxReceiveCount     = 4
  })
}

resource "aws_sqs_queue" "audio_queue_deadletter" {
  name = "${local.name}-audio-queue-deadletter"
}

resource "aws_sqs_queue_redrive_allow_policy" "audio_queue_redrive_allow_policy" {
  queue_url = aws_sqs_queue.audio_queue_deadletter.id

  redrive_allow_policy = jsonencode({
    redrivePermission = "byQueue",
    sourceQueueArns   = [aws_sqs_queue.audio_queue.arn]
  })
}
