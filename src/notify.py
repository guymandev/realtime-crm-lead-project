# src/notify.py

import os
from typing import Any

import boto3


class NotificationError(RuntimeError):
    """Raised when a lead notification cannot be sent."""


ses_client = boto3.client("ses")


def format_lead_email_body(enriched_lead: dict[str, Any]) -> str:
    """
    Format the required lead notification email body.
    """

    return f"""New Lead Alert

Name: {enriched_lead.get("display_name")}
Lead ID: {enriched_lead.get("lead_id")}
Created Date: {enriched_lead.get("date_created")}
Label: {enriched_lead.get("status_label")}
Email: {enriched_lead.get("lead_email")}
Lead Owner: {enriched_lead.get("lead_owner")}
Funnel: {enriched_lead.get("funnel")}
"""


def send_email_notification(enriched_lead: dict[str, Any]) -> dict[str, Any]:
    """
    Send a lead notification email using Amazon SES.
    """

    sender = os.environ.get("SES_FROM_EMAIL")
    recipient = os.environ.get("NOTIFICATION_TO_EMAIL")

    if not sender:
        raise NotificationError("Missing SES_FROM_EMAIL environment variable.")

    if not recipient:
        raise NotificationError("Missing NOTIFICATION_TO_EMAIL environment variable.")

    lead_name = enriched_lead.get("display_name") or "New Lead"
    lead_id = enriched_lead.get("lead_id") or "unknown"

    subject = f"New Lead Alert: {lead_name} ({lead_id})"
    body = format_lead_email_body(enriched_lead)

    response = ses_client.send_email(
        Source=sender,
        Destination={
            "ToAddresses": [recipient]
        },
        Message={
            "Subject": {
                "Data": subject,
                "Charset": "UTF-8"
            },
            "Body": {
                "Text": {
                    "Data": body,
                    "Charset": "UTF-8"
                }
            }
        }
    )

    return {
        "message_id": response.get("MessageId"),
        "recipient": recipient,
        "subject": subject
    }


def send_notification(enriched_lead: dict[str, Any]) -> dict[str, Any]:
    """
    Dispatch notification based on NOTIFICATION_MODE.

    Supported modes:
      email    -> send email via SES
      disabled -> skip notification
    """

    notification_mode = os.environ.get("NOTIFICATION_MODE", "email").lower()

    if notification_mode == "email":
        return send_email_notification(enriched_lead)

    if notification_mode == "disabled":
        return {
            "message": "Notification disabled"
        }

    raise NotificationError(
        f"Unsupported NOTIFICATION_MODE={notification_mode}. "
        "Expected 'email' or 'disabled'."
    )