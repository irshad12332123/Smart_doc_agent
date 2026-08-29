import boto3
from config.settings import AWS_REGION

aws_s3_client = boto3.client("s3", region_name=AWS_REGION)

