"""AWS client utilities for Lambda functions."""
import os
import boto3
from typing import Optional
from functools import lru_cache


@lru_cache(maxsize=1)
def get_elbv2_client():
    """Get cached ELBv2 client."""
    return boto3.client('elbv2')


@lru_cache(maxsize=1)
def get_ec2_client():
    """Get cached EC2 client."""
    return boto3.client('ec2')


@lru_cache(maxsize=1)
def get_ssm_client():
    """Get cached SSM client."""
    return boto3.client('ssm')


@lru_cache(maxsize=1)
def get_autoscaling_client():
    """Get cached Auto Scaling client."""
    return boto3.client('autoscaling')


@lru_cache(maxsize=1)
def get_cloudwatch_client():
    """Get cached CloudWatch client."""
    return boto3.client('cloudwatch')


@lru_cache(maxsize=1)
def get_dynamodb_client():
    """Get cached DynamoDB client."""
    return boto3.client('dynamodb')


@lru_cache(maxsize=1)
def get_dynamodb_resource():
    """Get cached DynamoDB resource."""
    return boto3.resource('dynamodb')


@lru_cache(maxsize=1)
def get_sns_client():
    """Get cached SNS client."""
    return boto3.client('sns')


def get_table(table_name: str):
    """Get DynamoDB table resource."""
    dynamodb = get_dynamodb_resource()
    return dynamodb.Table(table_name)


def get_region() -> str:
    """Get current AWS region."""
    return os.environ.get('AWS_REGION', boto3.Session().region_name or 'us-east-1')

