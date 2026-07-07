import json
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    try:
        logger.info("Received event: %s", json.dumps(event))

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json"
            },
            "body": json.dumps({
                "message": "Webhook received"
            })
        }

    except Exception:
        logger.exception("Unhandled error while processing webhook event")

        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json"
            },
            "body": json.dumps({
                "message": "Internal server error"
            })
        }