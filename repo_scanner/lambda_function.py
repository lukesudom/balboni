import json
import subprocess
import logging
import os
from urllib.parse import urlparse
import requests

logger = logging.getLogger()
logger.setLevel(logging.INFO)

DISCORD_WEBHOOK_URL = os.environ.get('DISCORD_WEBHOOK_URL')


def run_trufflehog(repo_url):
    logger.info(f"Starting TruffleHog scan on {repo_url}")
    try:
        git_username = os.environ.get('GIT_USERNAME')
        git_token = os.environ.get('GIT_TOKEN')

        if git_username and git_token:
            parsed_url = urlparse(repo_url)
            auth_url = f"{parsed_url.scheme}://{git_username}:{git_token}@{parsed_url.netloc}{parsed_url.path}"
            logger.info(f"Using authenticated URL for scanning")
        else:
            auth_url = repo_url
            logger.warning("Git credentials not found, attempting unauthenticated scan")

        command = [
            "trufflehog", "git",
            "--no-update",
            "--no-verification",
            "--max-depth=1000",
            "--json",
            auth_url
        ]

        print_command = ' '.join(command).replace(auth_url, repo_url)
        print(f"Running command: {print_command}")

        print(f"Scanning URL: {repo_url}")

        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=300
        )

        print(f"TruffleHog exit code: {result.returncode}")
        print(f"TruffleHog stdout:\n{result.stdout}")
        print(f"TruffleHog stderr:\n{result.stderr}")

        logger.info(f"TruffleHog scan completed for {repo_url}")

        if result.returncode != 0:
            logger.warning(f"TruffleHog exited with non-zero status: {result.returncode}")
            logger.warning(f"stderr: {result.stderr}")

        return result.stdout
    except subprocess.TimeoutExpired:
        logger.error(f"TruffleHog scan timed out for {repo_url}")
        return None
    except subprocess.CalledProcessError as e:
        logger.error(f"TruffleHog scan failed for {repo_url}: {e}")
        logger.error(f"stdout: {e.stdout}")
        logger.error(f"stderr: {e.stderr}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error during TruffleHog scan for {repo_url}: {str(e)}")
        return None

def format_trufflehog_result(result):
    formatted = f"```json\n"
    formatted += json.dumps(result, indent=2)
    formatted += "\n```"
    return formatted

def send_to_discord(message):
    if not DISCORD_WEBHOOK_URL:
        logger.error("Discord webhook URL is not set")
        return

    max_length = 2000
    chunks = [message[i:i + max_length] for i in range(0, len(message), max_length)]

    for chunk in chunks:
        data = {
            "content": chunk
        }

        response = requests.post(DISCORD_WEBHOOK_URL, json=data)
        if response.status_code == 204:
            logger.info("Message chunk sent to Discord successfully")
        else:
            logger.error(f"Failed to send message chunk to Discord. Status code: {response.status_code}")


def lambda_handler(event, context):
    logger.info("Lambda function invoked")
    logger.info(f"Received event: {json.dumps(event)}")

    all_results = []

    for record in event['Records']:
        message = json.loads(record['body'])
        repo_url = message['repo_url']
        repo_name = message['repo_name']

        logger.info(f"Processing repository: {repo_name}")

        try:
            trufflehog_output = run_trufflehog(repo_url)

            if trufflehog_output:
                logger.info(f"TruffleHog results for {repo_url}:\n{trufflehog_output}")
                results = [json.loads(line) for line in trufflehog_output.strip().split('\n')]
                all_results.extend(results)

                discord_message = f"TruffleHog scan results for {repo_name}:\n\n"
                for result in results:
                    file = result['SourceMetadata']['Data']['Git']['file']
                    commit = result['SourceMetadata']['Data']['Git']['commit']
                    commit_short = commit[:7]
                    detector = result['DetectorName']

                    commit_url = f"{repo_url}/commit/{commit}"

                    discord_message += f"Secret found in {file} (commit: {commit_short})\n"
                    discord_message += f"Detector: {detector}\n"
                    discord_message += f"Commit URL: {commit_url}\n"
                    discord_message += format_trufflehog_result(result)
                    discord_message += "\n\n"

                send_to_discord(discord_message)
            else:
                logger.info(f"No output from TruffleHog for {repo_url}")
                send_to_discord(f"No secrets found in repository: {repo_name}")

        except Exception as e:
            error_message = f"Error processing repository {repo_url}: {str(e)}"
            logger.error(error_message)
            send_to_discord(error_message)

    logger.info("Lambda function execution completed")
    return {
        'statusCode': 200,
        'body': json.dumps({
            'message': 'Scan completed',
            'results': all_results
        })
    }
