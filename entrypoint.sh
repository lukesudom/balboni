#!/bin/bash

WEBHOOK_RECEIVER_REPO=$1
REPO_SCANNER_REPO=$2
REGION=$3
IMAGE_TAG=$4

# Build and push webhook receiver
docker build -t webhook-receiver:${IMAGE_TAG} webhook_receiver
docker tag webhook-receiver:${IMAGE_TAG} ${WEBHOOK_RECEIVER_REPO}:${IMAGE_TAG}
aws ecr get-login-password --region ${REGION} | docker login --username AWS --password-stdin ${WEBHOOK_RECEIVER_REPO}
docker push ${WEBHOOK_RECEIVER_REPO}:${IMAGE_TAG}

# Build and push repo scanner
docker build -t repo-scanner:${IMAGE_TAG} repo_scanner
docker tag repo-scanner:${IMAGE_TAG} ${REPO_SCANNER_REPO}:${IMAGE_TAG}
aws ecr get-login-password --region ${REGION} | docker login --username AWS --password-stdin ${REPO_SCANNER_REPO}
docker push ${REPO_SCANNER_REPO}:${IMAGE_TAG}