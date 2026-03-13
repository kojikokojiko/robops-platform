"""共通テストフィクスチャ"""

from __future__ import annotations

import os

import boto3
import moto
import pytest

# テスト用環境変数 (他のモジュールより先にセット)
os.environ.update({
    "ENV": "test",
    "AWS_DEFAULT_REGION": "ap-northeast-1",
    "AWS_ACCESS_KEY_ID": "testing",
    "AWS_SECRET_ACCESS_KEY": "testing",
    "DYNAMODB_TABLE_ROBOTS": "test-robots",
    "DYNAMODB_TABLE_SCHEDULES": "test-schedules",
    "DYNAMODB_TABLE_OTA_JOBS": "test-ota-jobs",
    "DYNAMODB_TABLE_WS_CONNECTIONS": "test-ws-connections",
    "TIMESTREAM_DATABASE": "test-db",
    "TIMESTREAM_TABLE": "telemetry",
    "OTA_FIRMWARE_BUCKET": "test-firmware-bucket",
    "IOT_ENDPOINT": "test.iot.ap-northeast-1.amazonaws.com",
    "SCHEDULER_TRIGGER_LAMBDA_ARN": "arn:aws:lambda:ap-northeast-1:123456789012:function:test",
    "EVENTBRIDGE_SCHEDULER_ROLE_ARN": "arn:aws:iam::123456789012:role/test",
})


@pytest.fixture()
def aws_mock():
    """DynamoDB / S3 / IoT を moto でモック"""
    with moto.mock_aws():
        _setup_dynamodb()
        _setup_s3()
        yield


def _setup_dynamodb() -> None:
    ddb = boto3.resource("dynamodb", region_name="ap-northeast-1")

    ddb.create_table(
        TableName="test-robots",
        BillingMode="PAY_PER_REQUEST",
        KeySchema=[{"AttributeName": "robot_id", "KeyType": "HASH"}],
        AttributeDefinitions=[
            {"AttributeName": "robot_id", "AttributeType": "S"},
            {"AttributeName": "status", "AttributeType": "S"},
        ],
        GlobalSecondaryIndexes=[{
            "IndexName": "status-index",
            "KeySchema": [{"AttributeName": "status", "KeyType": "HASH"}],
            "Projection": {"ProjectionType": "ALL"},
        }],
    )

    ddb.create_table(
        TableName="test-schedules",
        BillingMode="PAY_PER_REQUEST",
        KeySchema=[
            {"AttributeName": "schedule_id", "KeyType": "HASH"},
            {"AttributeName": "robot_id", "KeyType": "RANGE"},
        ],
        AttributeDefinitions=[
            {"AttributeName": "schedule_id", "AttributeType": "S"},
            {"AttributeName": "robot_id", "AttributeType": "S"},
        ],
        GlobalSecondaryIndexes=[{
            "IndexName": "robot-index",
            "KeySchema": [{"AttributeName": "robot_id", "KeyType": "HASH"}],
            "Projection": {"ProjectionType": "ALL"},
        }],
    )

    ddb.create_table(
        TableName="test-ota-jobs",
        BillingMode="PAY_PER_REQUEST",
        KeySchema=[
            {"AttributeName": "job_id", "KeyType": "HASH"},
            {"AttributeName": "robot_id", "KeyType": "RANGE"},
        ],
        AttributeDefinitions=[
            {"AttributeName": "job_id", "AttributeType": "S"},
            {"AttributeName": "robot_id", "AttributeType": "S"},
        ],
        GlobalSecondaryIndexes=[{
            "IndexName": "robot-index",
            "KeySchema": [{"AttributeName": "robot_id", "KeyType": "HASH"}],
            "Projection": {"ProjectionType": "ALL"},
        }],
    )

    ddb.create_table(
        TableName="test-ws-connections",
        BillingMode="PAY_PER_REQUEST",
        KeySchema=[{"AttributeName": "connection_id", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "connection_id", "AttributeType": "S"}],
    )


def _setup_s3() -> None:
    s3 = boto3.client("s3", region_name="ap-northeast-1")
    s3.create_bucket(
        Bucket="test-firmware-bucket",
        CreateBucketConfiguration={"LocationConstraint": "ap-northeast-1"},
    )
