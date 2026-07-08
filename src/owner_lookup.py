# src/owner_lookup.py

import json
import os
import urllib.error
import urllib.request
from typing import Any

import boto3


class OwnerLookupError(RuntimeError):
    """Raised when lead owner lookup data cannot be retrieved or parsed."""


s3_client = boto3.client("s3")


def build_owner_lookup_url(lead_id: str) -> str:
    if not lead_id:
        raise OwnerLookupError("Cannot build owner lookup URL without lead_id.")

    return f"https://dea-lead-owner.s3.us-east-1.amazonaws.com/{lead_id}.json"


def fetch_owner_lookup_from_public_url(
    lead_id: str,
    timeout_seconds: int = 10
) -> dict[str, Any]:
    """
    Fetch lead-owner lookup JSON from the required public S3 URL.

    Production requirement:
    https://dea-lead-owner.s3.us-east-1.amazonaws.com/{lead_id}.json
    """

    url = build_owner_lookup_url(lead_id)

    try:
        with urllib.request.urlopen(url, timeout=timeout_seconds) as response:
            body = response.read().decode("utf-8")
            return json.loads(body)

    except urllib.error.HTTPError as exc:
        raise OwnerLookupError(
            f"Owner lookup failed for lead_id={lead_id}. HTTP status={exc.code}"
        ) from exc

    except urllib.error.URLError as exc:
        raise OwnerLookupError(
            f"Owner lookup request failed for lead_id={lead_id}: {exc.reason}"
        ) from exc

    except json.JSONDecodeError as exc:
        raise OwnerLookupError(
            f"Owner lookup response was not valid JSON for lead_id={lead_id}."
        ) from exc


def fetch_owner_lookup_from_s3(
    lead_id: str,
    bucket_name: str,
    prefix: str = "lookup"
) -> dict[str, Any]:
    """
    Fetch lead-owner lookup JSON from our dev/test S3 bucket.

    Example:
    s3://crm-lead-notification/lookup/lead_test123.json
    """

    if not lead_id:
        raise OwnerLookupError("Cannot fetch owner lookup without lead_id.")

    if not bucket_name:
        raise OwnerLookupError("Missing lookup bucket name.")

    clean_prefix = prefix.strip("/")
    key = f"{clean_prefix}/{lead_id}.json" if clean_prefix else f"{lead_id}.json"

    try:
        response = s3_client.get_object(Bucket=bucket_name, Key=key)
        body = response["Body"].read().decode("utf-8")
        return json.loads(body)

    except s3_client.exceptions.NoSuchKey as exc:
        raise OwnerLookupError(
            f"Owner lookup file not found. bucket={bucket_name}, key={key}"
        ) from exc

    except json.JSONDecodeError as exc:
        raise OwnerLookupError(
            f"Owner lookup S3 object was not valid JSON. bucket={bucket_name}, key={key}"
        ) from exc

    except Exception as exc:
        raise OwnerLookupError(
            f"Failed to fetch owner lookup from S3. bucket={bucket_name}, key={key}, error={exc}"
        ) from exc


def fetch_owner_lookup(lead_id: str) -> dict[str, Any]:
    """
    Fetch lead-owner lookup data.

    Modes:
      public_url = required project lookup URL
      s3         = local/dev lookup file in our own S3 bucket

    Environment variables:
      OWNER_LOOKUP_MODE=s3 or public_url
      OWNER_LOOKUP_BUCKET_NAME=crm-lead-notification
      OWNER_LOOKUP_PREFIX=lookup
    """

    lookup_mode = os.environ.get("OWNER_LOOKUP_MODE", "public_url").lower()

    if lookup_mode == "s3":
        bucket_name = os.environ.get("OWNER_LOOKUP_BUCKET_NAME")
        prefix = os.environ.get("OWNER_LOOKUP_PREFIX", "lookup")

        if not bucket_name:
            raise OwnerLookupError(
                "OWNER_LOOKUP_BUCKET_NAME is required when OWNER_LOOKUP_MODE=s3."
            )

        return fetch_owner_lookup_from_s3(
            lead_id=lead_id,
            bucket_name=bucket_name,
            prefix=prefix
        )

    if lookup_mode == "public_url":
        return fetch_owner_lookup_from_public_url(lead_id)

    raise OwnerLookupError(
        f"Unsupported OWNER_LOOKUP_MODE={lookup_mode}. Expected 'public_url' or 's3'."
    )