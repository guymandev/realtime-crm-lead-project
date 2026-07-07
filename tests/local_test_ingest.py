# local_test_ingest.py

import json
from crm_webhook_ingest.handler import lambda_handler


with open("events/sample_api_gateway_event.json", "r") as f:
    event = json.load(f)

response = lambda_handler(event, None)

print(json.dumps(response, indent=2))