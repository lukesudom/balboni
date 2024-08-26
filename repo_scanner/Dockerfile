FROM trufflesecurity/trufflehog:latest as trufflehog
FROM public.ecr.aws/lambda/python:3.10
COPY --from=trufflehog /usr/bin/trufflehog /usr/local/bin/trufflehog

RUN yum update -y && \
    yum install -y git && \
    yum clean all

COPY requirements.txt ${LAMBDA_TASK_ROOT}
RUN pip install --no-cache-dir -r requirements.txt

COPY lambda_function.py ${LAMBDA_TASK_ROOT}

CMD [ "lambda_function.lambda_handler" ]