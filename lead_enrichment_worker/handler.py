# lead_enrichment_worker/handler.py

import json
import logging
from typing import Any

import boto3

from src.enrich_lead import LeadEnrichmentError, build_enriched_s3_key, enrich_lead
from src.owner_lookup import OwnerLookupError, fetch_owner_lookup

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3_client = boto3.client("s3")


def _read_json_from_s3(bucket: str, key: str) -> dict[str, Any]:
    response = s3_client.get_object(Bucket=bucket, Key=key)
    body = response["Body"].read().decode("utf-8")
    return json.loads(body)


def _write_json_to_s3(bucket: str, key: str, payload: dict[str, Any]) -> None:
    s3_client.put_object(
        Bucket=bucket,
        Key=key,
        Body=json.dumps(payload, indent=2).encode("utf-8"),
        ContentType="application/json"
    )


def _process_record(record: dict[str, Any]) -> dict[str, Any]:
    message_body = json.loads(record["body"])

    lead_id = message_body["lead_id"]
    raw_bucket = message_body["raw_bucket"]
    raw_s3_key = message_body["raw_s3_key"]

    logger.info(
        "Processing delayed lead enrichment. lead_id=%s raw_bucket=%s raw_s3_key=%s",
        lead_id,
        raw_bucket,
        raw_s3_key
    )

    close_payload = _read_json_from_s3(raw_bucket, raw_s3_key)
    owner_lookup = fetch_owner_lookup(lead_id)
    enriched_payload = enrich_lead(close_payload, owner_lookup)

    enriched_s3_key = build_enriched_s3_key(lead_id)

    _write_json_to_s3(
        bucket=raw_bucket,
        key=enriched_s3_key,
        payload=enriched_payload
    )

    logger.info(
        "Stored enriched lead data. bucket=%s key=%s lead_id=%s",
        raw_bucket,
        enriched_s3_key,
        lead_id
    )

    return {
        "lead_id": lead_id,
        "raw_s3_key": raw_s3_key,
        "enriched_s3_key": enriched_s3_key
    }


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """
    Lambda handler for SQS-triggered lead enrichment.

    Expected SQS message body:
    {
      "lead_id": "...",
      "raw_bucket": "crm-lead-notification",
      "raw_s3_key": "source/crm_event_....json"
    }
    """

    logger.info("Received SQS event: %s", json.dumps(event))

    results = []
    failures = []

    for record in event.get("Records", []):
        message_id = record.get("messageId")

        try:
            result = _process_record(record)
            results.append(result)

        except (json.JSONDecodeError, KeyError, OwnerLookupError, LeadEnrichmentError) as exc:
            logger.exception(
                "Failed to process SQS record. message_id=%s error=%s",
                message_id,
                str(exc)
            )
            failures.append({
                "message_id": message_id,
                "error": str(exc)
            })

        except Exception as exc:
            logger.exception(
                "Unexpected failure processing SQS record. message_id=%s",
                message_id
            )
            failures.append({
                "message_id": message_id,
                "error": str(exc)
            })

    if failures:
        # Raising here tells Lambda/SQS the batch was not fully successful.
        # Later we can improve this with partial batch response handling.
        raise RuntimeError(f"Failed to process {len(failures)} SQS record(s): {failures}")

    return {
        "processed_count": len(results),
        "results": results
    }