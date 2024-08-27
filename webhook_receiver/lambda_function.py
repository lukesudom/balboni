import json
import os
import boto3
import requests
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

sqs = boto3.client('sqs')
# DISCORD_WEBHOOK_URL = os.environ['DISCORD_WEBHOOK_URL']
SQS_QUEUE_URL = os.environ['SQS_QUEUE_URL']
LOGGING_DISCORD_WEBHOOK_URL = os.environ['LOGGING_DISCORD_WEBHOOK_URL']


def send_to_discord(message, webhook):
    if not LOGGING_DISCORD_WEBHOOK_URL:
        logger.error(f'Logging webhook not set')
    response = requests.post(webhook, json={"content": message})
    if response.status_code == 204:
        logger.info('Posted successfully to discord')
    else:
        logger.error(f'Failed to post to discord {response.status_code}{response.text}')


def lambda_handler(event, context):
    try:
        body = json.loads(event['body'])
        logger.info(body)

        send_to_discord(f"Webhook received {body['repo']['name']}", LOGGING_DISCORD_WEBHOOK_URL)

        sqs_message = {
            'repo_url': body['repo']['url']['web'],
            'repo_name': body['repo']['name']
        }

        sqs_response = sqs.send_message(
            QueueUrl=SQS_QUEUE_URL,
            MessageBody=json.dumps(sqs_message)
        )

        logger.info(f"Message sent to SQS: {sqs_response['MessageId']}")
        send_to_discord(f"Message sent to SQS {sqs_response['MessageId']}", LOGGING_DISCORD_WEBHOOK_URL)

        return {
            'statusCode': 200,
            'body': json.dumps('Webhook received, sent to Discord, and queued for scanning')
        }
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse incoming JSON: {str(e)}")
        send_to_discord(f"Failed to parse incoming JSON: {str(e)}", LOGGING_DISCORD_WEBHOOK_URL)
        return {
            'statusCode': 400,
            'body': json.dumps('Invalid JSON in request body')
        }
    except requests.RequestException as e:
        logger.error(f"Failed to send message to Discord: {str(e)}")
        send_to_discord(f"Failed to send message to Discord: {str(e)}", LOGGING_DISCORD_WEBHOOK_URL)
        return {
            'statusCode': 500,
            'body': json.dumps('Failed to send message to Discord')
        }
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        send_to_discord(f"Unexpected error: {str(e)}", LOGGING_DISCORD_WEBHOOK_URL)
        return {
            'statusCode': 500,
            'body': json.dumps('An unexpected error occurred')
        }