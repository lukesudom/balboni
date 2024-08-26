import json
import os
import boto3
import requests
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

sqs = boto3.client('sqs')
DISCORD_WEBHOOK_URL = os.environ['DISCORD_WEBHOOK_URL']
SQS_QUEUE_URL = os.environ['SQS_QUEUE_URL']


def lambda_handler(event, context):
    try:
        body = json.loads(event['body'])
        logger.info(body)

        message = f"Webhook received {body['repo']['name']}"
        discord_response = requests.post(DISCORD_WEBHOOK_URL, json={'content': message})
        discord_response.raise_for_status()

        sqs_message = {
            'repo_url': body['repo']['url']['web'],
            'repo_name': body['repo']['name']
        }

        sqs_response = sqs.send_message(
            QueueUrl=SQS_QUEUE_URL,
            MessageBody=json.dumps(sqs_message)
        )

        logger.info(f"Message sent to SQS: {sqs_response['MessageId']}")

        return {
            'statusCode': 200,
            'body': json.dumps('Webhook received, sent to Discord, and queued for scanning')
        }
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse incoming JSON: {str(e)}")
        return {
            'statusCode': 400,
            'body': json.dumps('Invalid JSON in request body')
        }
    except requests.RequestException as e:
        logger.error(f"Failed to send message to Discord: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps('Failed to send message to Discord')
        }
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps('An unexpected error occurred')
        }