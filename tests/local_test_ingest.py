# tests/local_test_ingest.py

import json

from crm_webhook_ingest.handler import lambda_handler
from src.parse_close_event import parse_and_summarize


with open("events/sample_api_gateway_event.json", "r") as f:
    event = json.load(f)

response = lambda_handler(event, None)

print("Lambda response:")
print(json.dumps(response, indent=2))

close_payload, lead_summary, raw_s3_key = parse_and_summarize(event)

print("\nParsed Close payload:")
print(json.dumps(close_payload, indent=2))

print("\nLead summary:")
print(json.dumps(lead_summary, indent=2))

print("\nRaw S3 key:")
print(raw_s3_key)