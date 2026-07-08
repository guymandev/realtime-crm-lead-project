# tests/local_test_enrichment_worker.py

import json

from lead_enrichment_worker.handler import lambda_handler


with open("events/sample_sqs_event.json", "r") as f:
    event = json.load(f)

response = lambda_handler(event, None)

print(json.dumps(response, indent=2))