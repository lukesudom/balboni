import json
import os
import boto3
import requests

sqs = boto3.client('sqs')
DISCORD_WEBHOOK_URL = os.environ['DISCORD_WEBHOOK_URL']
SQS_QUEUE_URL = os.environ['SQS_QUEUE_URL']


def lambda_handler(event, context):
    # Extract the webhook payload
    body = json.loads(event['body'])

    # Prepare the message for Discord
    message = f"Received webhook from Hugging Face:\n```json\n{json.dumps(body, indent=2)}\n```"

    # Send to Discord
    requests.post(DISCORD_WEBHOOK_URL, json={'content': message})

    # Prepare message for SQS
    sqs_message = {
        'repo_url': body['repo']['url']['web'],
        'repo_name': body['repo']['name']
    }

    # Send message to SQS
    sqs.send_message(
        QueueUrl=SQS_QUEUE_URL,
        MessageBody=json.dumps(sqs_message)
    )

    return {
        'statusCode': 200,
        'body': json.dumps('Webhook received, sent to Discord, and queued for scanning')
    }