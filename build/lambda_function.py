# crm_webhook_ingest/handler.py

import json
import logging
import os
from typing import Any

import boto3

from src.parse_close_event import WebhookParseError, parse_and_summarize

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3_client = boto3.client("s3")
sqs_client = boto3.client("sqs")


def _response(
    status_code: int,
    message: str,
    extra_body: dict[str, Any] | None = None
) -> dict[str, Any]:
    body = {"message": message}

    if extra_body:
        body.update(extra_body)

    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json"
        },
        "body": json.dumps(body)
    }


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    try:
        logger.info("Received event: %s", json.dumps(event))

        raw_bucket_name = os.environ.get("RAW_BUCKET_NAME")
        delay_queue_url = os.environ.get("DELAY_QUEUE_URL")

        if not raw_bucket_name:
            logger.error("Missing required environment variable: RAW_BUCKET_NAME")
            return _response(500, "Server configuration error")

        if not delay_queue_url:
            logger.error("Missing required environment variable: DELAY_QUEUE_URL")
            return _response(500, "Server configuration error")

        close_payload, lead_summary, raw_s3_key = parse_and_summarize(event)

        s3_client.put_object(
            Bucket=raw_bucket_name,
            Key=raw_s3_key,
            Body=json.dumps(close_payload, indent=2).encode("utf-8"),
            ContentType="application/json"
        )

        logger.info(
            "Stored CRM webhook event in S3. bucket=%s key=%s lead_id=%s",
            raw_bucket_name,
            raw_s3_key,
            lead_summary["lead_id"]
        )

        sqs_message = {
            "lead_id": lead_summary["lead_id"],
            "raw_bucket": raw_bucket_name,
            "raw_s3_key": raw_s3_key
        }

        sqs_response = sqs_client.send_message(
            QueueUrl=delay_queue_url,
            MessageBody=json.dumps(sqs_message),
            DelaySeconds=600
        )

        message_id = sqs_response.get("MessageId")

        logger.info(
            "Sent delayed SQS message. queue_url=%s message_id=%s lead_id=%s",
            delay_queue_url,
            message_id,
            lead_summary["lead_id"]
        )

        return _response(
            200,
            "Webhook received, stored, and queued",
            {
                "lead_id": lead_summary["lead_id"],
                "s3_key": raw_s3_key,
                "sqs_message_id": message_id
            }
        )

    except WebhookParseError as exc:
        logger.warning("Invalid webhook payload: %s", str(exc))

        return _response(
            400,
            "Invalid webhook payload",
            {
                "error": str(exc)
            }
        )

    except Exception:
        logger.exception("Unhandled error while processing webhook event")

        return _response(500, "Internal server error")