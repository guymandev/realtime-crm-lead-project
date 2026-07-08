# src/parse_close_event.py

import base64
import json
from typing import Any


class WebhookParseError(ValueError):
    """Raised when the incoming webhook event cannot be parsed safely."""


def parse_api_gateway_event(api_event: dict[str, Any]) -> dict[str, Any]:
    """
    Parse an API Gateway/Lambda event and return the Close CRM webhook body.

    API Gateway sends the external POST body as api_event["body"].
    That body is usually a JSON string.
    """

    if not isinstance(api_event, dict):
        raise WebhookParseError("API Gateway event must be a dictionary.")

    body = api_event.get("body")

    if body is None:
        raise WebhookParseError("Missing request body.")

    if api_event.get("isBase64Encoded") is True:
        try:
            body = base64.b64decode(body).decode("utf-8")
        except Exception as exc:
            raise WebhookParseError("Unable to decode base64 request body.") from exc

    if isinstance(body, str):
        try:
            close_payload = json.loads(body)
        except json.JSONDecodeError as exc:
            raise WebhookParseError("Request body is not valid JSON.") from exc
    elif isinstance(body, dict):
        # Useful for local tests where we may pass the body as an already-parsed dict.
        close_payload = body
    else:
        raise WebhookParseError("Request body must be a JSON string or dictionary.")

    return close_payload


def extract_lead_summary(close_payload: dict[str, Any]) -> dict[str, Any]:
    """
    Extract the key lead fields from a Close CRM webhook payload.
    """

    try:
        event = close_payload["event"]
    except KeyError as exc:
        raise WebhookParseError("Missing 'event' object in Close payload.") from exc

    lead_id = event.get("lead_id") or event.get("object_id")

    if not lead_id:
        raise WebhookParseError("Missing lead_id in Close event.")

    data = event.get("data") or {}

    return {
        "subscription_id": close_payload.get("subscription_id"),
        "event_id": event.get("id"),
        "lead_id": lead_id,
        "object_type": event.get("object_type"),
        "action": event.get("action"),
        "display_name": data.get("display_name"),
        "date_created": data.get("date_created") or event.get("date_created"),
        "status_label": data.get("status_label"),
        "funnel": data.get("custom.cf_am3UgCUhyM5iNDtAPL84enDjUrZx1JsyVZ9uD9TbYwG"),
    }


def build_raw_s3_key(lead_id: str) -> str:
    """
    Build the required S3 object key for the raw/source CRM event.
    Requirement filename pattern: crm_event_{lead_id}.json
    """

    if not lead_id:
        raise WebhookParseError("Cannot build S3 key without lead_id.")

    return f"source/crm_event_{lead_id}.json"


def parse_and_summarize(api_event: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], str]:
    """
    Convenience function for Lambda:
    - parse API Gateway event
    - extract lead summary
    - build target S3 key

    Returns:
        close_payload, lead_summary, raw_s3_key
    """

    close_payload = parse_api_gateway_event(api_event)
    lead_summary = extract_lead_summary(close_payload)
    raw_s3_key = build_raw_s3_key(lead_summary["lead_id"])

    return close_payload, lead_summary, raw_s3_key