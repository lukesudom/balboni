# balboni

I've been watching you for a while now...

"You haven't hit shit yet" (credentials)

## Description

Balboni is a modular scanner for git repositories currently working with repositories hosted on Huggignface.

It's basic architecture is a API gateway that receives post requests from a Huggingface Webhook once received we parse the request to extract the repo url.

From here we run a scan using Trufflehog on the repository to extract secrets.

Rate limiting and queuing is handled by an Amazon SQS queue to ensure first in first out.

## Deployment

WIP - Terraform files to come for basic deployment.

