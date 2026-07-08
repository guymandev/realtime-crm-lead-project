# src/enrich_lead.py

from typing import Any


class LeadEnrichmentError(ValueError):
    """Raised when lead enrichment cannot be completed."""


def extract_crm_lead_fields(close_payload: dict[str, Any]) -> dict[str, Any]:
    """
    Extract required lead fields from the raw Close webhook payload stored in S3.
    """

    event = close_payload.get("event") or {}
    data = event.get("data") or {}

    lead_id = event.get("lead_id") or event.get("object_id") or data.get("id")

    if not lead_id:
        raise LeadEnrichmentError("Missing lead_id in raw CRM payload.")

    return {
        "display_name": data.get("display_name"),
        "lead_id": lead_id,
        "date_created": data.get("date_created") or event.get("date_created"),
        "status_label": data.get("status_label"),
    }


def enrich_lead(
    close_payload: dict[str, Any],
    owner_lookup: dict[str, Any]
) -> dict[str, Any]:
    """
    Merge raw CRM webhook data with public S3 lead-owner lookup data.
    """

    crm_fields = extract_crm_lead_fields(close_payload)

    lead_id = crm_fields["lead_id"]
    lookup_lead_id = owner_lookup.get("lead_id")

    if lookup_lead_id and lookup_lead_id != lead_id:
        raise LeadEnrichmentError(
            f"Lead ID mismatch. raw={lead_id}, lookup={lookup_lead_id}"
        )

    return {
        "display_name": crm_fields.get("display_name") or owner_lookup.get("display_name"),
        "lead_id": lead_id,
        "date_created": crm_fields.get("date_created") or owner_lookup.get("date_created"),
        "status_label": crm_fields.get("status_label") or owner_lookup.get("status_label"),
        "lead_email": owner_lookup.get("lead_email"),
        "lead_owner": owner_lookup.get("lead_owner"),
        "funnel": owner_lookup.get("funnel"),
    }


def build_enriched_s3_key(lead_id: str) -> str:
    if not lead_id:
        raise LeadEnrichmentError("Cannot build enriched S3 key without lead_id.")

    return f"target/enriched_lead_{lead_id}.json"