import json
import os
import subprocess
import shutil
from git import Repo, GitCommandError
import logging
from urllib.parse import urlparse

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def run_trufflehog(repo_path):
    logger.info(f"Starting TruffleHog scan on {repo_path}")
    try:
        result = subprocess.run(
            ["trufflehog", "git", "--only-verified", "--max-depth=1000", "--concurrency=10", "--debug",
             f"file://{repo_path}"],
            capture_output=True,
            text=True,
            timeout=300  # 5 minutes timeout
        )
        logger.info(f"TruffleHog scan completed for {repo_path}")
        return result.stdout
    except subprocess.TimeoutExpired:
        logger.error(f"TruffleHog scan timed out for {repo_path}")
        return None
    except subprocess.CalledProcessError as e:
        logger.error(f"TruffleHog scan failed for {repo_path}: {e}")
        return None


def clean_directory(path):
    logger.info(f"Cleaning directory: {path}")
    if os.path.exists(path):
        try:
            shutil.rmtree(path)
            logger.info(f"Successfully removed existing directory: {path}")
        except Exception as e:
            logger.error(f"Error removing directory {path}: {str(e)}")
            raise


def clone_repository(repo_url, repo_path):
    logger.info(f"Cloning repository: {repo_url} to {repo_path}")
    try:
        git_username = os.environ.get('GIT_USERNAME')
        git_token = os.environ.get('GIT_TOKEN')

        if git_username and git_token:
            parsed_url = urlparse(repo_url)
            auth_url = f"{parsed_url.scheme}://{git_username}:{git_token}@{parsed_url.netloc}{parsed_url.path}"
            logger.info(f"Using authenticated URL for cloning")
            Repo.clone_from(auth_url, repo_path)
        else:
            logger.warning("Git credentials not found, attempting unauthenticated clone")
            Repo.clone_from(repo_url, repo_path)

        logger.info(f"Successfully cloned {repo_url}")
    except GitCommandError as e:
        logger.error(f"Git clone failed for {repo_url}: {str(e)}")
        raise


def lambda_handler(event, context):
    logger.info("Lambda function invoked")
    logger.info(f"Received event: {json.dumps(event)}")

    for record in event['Records']:
        # Parse the message from SQS
        message = json.loads(record['body'])
        repo_url = message['repo_url']
        repo_name = message['repo_name']

        logger.info(f"Processing repository: {repo_name}")

        # Clone the repository
        repo_path = f'/tmp/{repo_name}'

        try:
            # Clean existing directory if it exists
            clean_directory(repo_path)

            # Clone the repository
            clone_repository(repo_url, repo_path)

            # Run TruffleHog
            trufflehog_output = run_trufflehog(repo_path)

            if trufflehog_output:
                logger.info(f"TruffleHog results for {repo_url}:\n{trufflehog_output}")
                # Here you would typically send this to S3 or another storage service
            else:
                logger.info(f"No output from TruffleHog for {repo_url}")

        except Exception as e:
            logger.error(f"Error processing repository {repo_url}: {str(e)}")

        finally:
            # Clean up
            clean_directory(repo_path)

    logger.info("Lambda function execution completed")
    return {
        'statusCode': 200,
        'body': json.dumps('Scan completed')
    }