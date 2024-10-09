# balboni

I've been watching you for a while now...

## Description

Balboni is a modular scanner for git repositories currently working with repositories hosted on Huggignface.

It's basic architecture is a API gateway that receives post requests from a Huggingface Webhook once received we parse the request to extract the repo url.

From here we run a scan using Trufflehog on the repository to extract secrets.

Rate limiting and queuing is handled by an Amazon SQS queue to ensure first in first out.

## Deployment

Infrastructure deployment is done via terraform.

## Creating a Huggingface Webhook

1. Visit https://huggingface.co/settings/webhooks
2. Click `Add a new webhook`
3. Under Target repositories choose the repo you would like to monitor e.g facebook/* (you can add multiple orgs)
4. Add the API Gateway Webhook URL
5. Select the triggers - you want both Repo Update and PR's

## Future Development Ideas
- filtering already tested tokens to reduce noise.
- scanning only commits to improve performance.
- ability to dynamically add orgs / repositories to the webhook (maybe scrap or API).
