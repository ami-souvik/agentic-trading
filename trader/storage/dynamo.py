"""
DynamoDB read/write helpers for the NSE trader.

Single-table design: all entity types live in one table (`nse_trader`),
separated by PK/SK prefix conventions. Numbers stored as Decimal for
financial precision.

Entity PK/SK layout:
  POSITION  PK=TICKER#{symbol}   SK=DATE#{yyyy-mm-dd}
  DECISION  PK=DATE#{yyyy-mm-dd} SK=TICKER#{symbol}#AGENT#{name}
  TRADE     PK=DATE#{yyyy-mm-dd} SK=TRADE#{uuid}
  NAV       PK=DATE#{yyyy-mm-dd} SK=PORTFOLIO

Table name is read from settings.dynamo_table_name (env: DYNAMO_TABLE_NAME).
"""
from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any

import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

from trader.config.settings import get_settings

logger = logging.getLogger(__name__)


def _get_table(table_name: str):
    settings = get_settings()
    dynamodb = boto3.resource("dynamodb", region_name=settings.aws_region)
    return dynamodb.Table(table_name)


def _sanitize_floats(obj: Any) -> Any:
    """Recursively convert float → Decimal so boto3 accepts the item."""
    if isinstance(obj, float):
        return Decimal(str(obj))
    if isinstance(obj, dict):
        return {k: _sanitize_floats(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize_floats(v) for v in obj]
    return obj


def put_item(table_name: str, item: dict) -> None:
    """
    Write a single item to DynamoDB.
    Floats are auto-converted to Decimal (DynamoDB requirement).
    Raises on AWS errors; caller decides whether to retry.
    """
    settings = get_settings()
    if settings.dry_run:
        logger.debug("[DRY RUN] put_item → %s: %s", table_name, item.get("PK"))
        return

    table = _get_table(table_name)
    try:
        table.put_item(Item=_sanitize_floats(item))
    except ClientError as e:
        logger.error("DynamoDB put_item failed on %s: %s", table_name, e)
        raise


def get_item(table_name: str, pk: str, sk: str) -> dict | None:
    """
    Fetch a single item by its composite key. Returns None if not found.
    """
    table = _get_table(table_name)
    try:
        response = table.get_item(Key={"PK": pk, "SK": sk})
        return response.get("Item")
    except ClientError as e:
        logger.error("DynamoDB get_item failed on %s (PK=%s, SK=%s): %s", table_name, pk, sk, e)
        raise


def query_by_pk(
    table_name: str,
    pk: str,
    sk_begins_with: str | None = None,
    limit: int | None = None,
    scan_index_forward: bool = True,
) -> list[dict]:
    """
    Query all items with a given PK, optionally filtered by SK prefix.

    Args:
        table_name:         DynamoDB table name.
        pk:                 Partition key value.
        sk_begins_with:     Optional sort key prefix filter.
        limit:              Max number of items to return.
        scan_index_forward: True = ascending SK order (default).

    Returns:
        List of item dicts.
    """
    table = _get_table(table_name)
    kwargs: dict[str, Any] = {
        "KeyConditionExpression": Key("PK").eq(pk),
        "ScanIndexForward": scan_index_forward,
    }
    if sk_begins_with:
        kwargs["KeyConditionExpression"] &= Key("SK").begins_with(sk_begins_with)
    if limit:
        kwargs["Limit"] = limit

    items: list[dict] = []
    try:
        while True:
            response = table.query(**kwargs)
            items.extend(response.get("Items", []))
            last_key = response.get("LastEvaluatedKey")
            if not last_key or (limit and len(items) >= limit):
                break
            kwargs["ExclusiveStartKey"] = last_key
    except ClientError as e:
        logger.error("DynamoDB query failed on %s (PK=%s): %s", table_name, pk, e)
        raise

    return items[:limit] if limit else items


def update_item(
    table_name: str,
    pk: str,
    sk: str,
    updates: dict[str, Any],
) -> dict:
    """
    Partially update an existing item. Creates it if it doesn't exist.

    Args:
        table_name: DynamoDB table name.
        pk:         Partition key value.
        sk:         Sort key value.
        updates:    Dict of attribute_name → new_value to set.

    Returns:
        The updated item attributes.
    """
    settings = get_settings()
    if settings.dry_run:
        logger.debug("[DRY RUN] update_item → %s: PK=%s SK=%s", table_name, pk, sk)
        return {}

    updates = _sanitize_floats(updates)
    table = _get_table(table_name)

    # Build UpdateExpression and ExpressionAttributeValues dynamically
    set_parts = []
    expr_values: dict[str, Any] = {}
    expr_names: dict[str, str] = {}

    for i, (attr, value) in enumerate(updates.items()):
        placeholder = f":v{i}"
        name_placeholder = f"#n{i}"
        set_parts.append(f"{name_placeholder} = {placeholder}")
        expr_values[placeholder] = value
        expr_names[name_placeholder] = attr

    update_expr = "SET " + ", ".join(set_parts)

    try:
        response = table.update_item(
            Key={"PK": pk, "SK": sk},
            UpdateExpression=update_expr,
            ExpressionAttributeValues=expr_values,
            ExpressionAttributeNames=expr_names,
            ReturnValues="ALL_NEW",
        )
        return response.get("Attributes", {})
    except ClientError as e:
        logger.error("DynamoDB update_item failed on %s (PK=%s, SK=%s): %s", table_name, pk, sk, e)
        raise


def delete_item(table_name: str, pk: str, sk: str) -> None:
    """Delete an item by composite key. No-op if the item doesn't exist."""
    settings = get_settings()
    if settings.dry_run:
        logger.debug("[DRY RUN] delete_item → %s: PK=%s SK=%s", table_name, pk, sk)
        return

    table = _get_table(table_name)
    try:
        table.delete_item(Key={"PK": pk, "SK": sk})
    except ClientError as e:
        logger.error("DynamoDB delete_item failed on %s (PK=%s, SK=%s): %s", table_name, pk, sk, e)
        raise


def batch_write_items(table_name: str, items: list[dict]) -> None:
    """
    Write multiple items in batches of 25 (DynamoDB limit).
    Use for bulk inserts (e.g., archiving a full day's decisions).
    """
    settings = get_settings()
    if settings.dry_run:
        logger.debug("[DRY RUN] batch_write_items → %s: %d items", table_name, len(items))
        return

    table = _get_table(table_name)
    sanitized = [_sanitize_floats(item) for item in items]

    # DynamoDB batch_writer handles chunking and retries automatically
    try:
        with table.batch_writer() as batch:
            for item in sanitized:
                batch.put_item(Item=item)
    except ClientError as e:
        logger.error("DynamoDB batch_write failed on %s: %s", table_name, e)
        raise


def item_exists(table_name: str, pk: str, sk: str) -> bool:
    """Return True if an item with the given composite key exists."""
    item = get_item(table_name, pk, sk)
    return item is not None


# ─── Convenience wrappers — all write to the single master table ─────────────

def _table() -> str:
    """Return the master DynamoDB table name from settings."""
    return get_settings().dynamo_table_name


def put_position(item: dict) -> None:
    """Write/overwrite a POSITION item. Caller must set PK, SK, and type='POSITION'."""
    put_item(_table(), {**item, "type": "POSITION"})


def get_position(ticker: str, date_str: str) -> dict | None:
    """Fetch a position by ticker symbol and date string (yyyy-mm-dd)."""
    return get_item(_table(), pk=f"TICKER#{ticker}", sk=f"DATE#{date_str}")


def put_decision(item: dict) -> None:
    """Write/overwrite a DECISION item. Caller must set PK, SK."""
    put_item(_table(), {**item, "type": "DECISION"})


def get_decision(date_str: str, ticker: str, agent: str) -> dict | None:
    """Fetch a single agent decision for a ticker on a given date."""
    return get_item(
        _table(),
        pk=f"DATE#{date_str}",
        sk=f"TICKER#{ticker}#AGENT#{agent}",
    )


def get_decisions_for_date(date_str: str) -> list[dict]:
    """Return all DECISION items for a given trading date, sorted by SK."""
    return query_by_pk(_table(), pk=f"DATE#{date_str}", sk_begins_with="TICKER#")


def put_trade(item: dict) -> None:
    """Write a TRADE (simulated fill) item. Caller must set PK and SK=TRADE#{uuid}."""
    put_item(_table(), {**item, "type": "TRADE"})


def get_trades_for_date(date_str: str) -> list[dict]:
    """Return all TRADE items for a given trading date."""
    return query_by_pk(_table(), pk=f"DATE#{date_str}", sk_begins_with="TRADE#")


def put_nav(item: dict) -> None:
    """Write/overwrite a NAV (daily portfolio snapshot) item."""
    put_item(_table(), {**item, "type": "NAV"})


def get_nav(date_str: str) -> dict | None:
    """Fetch the NAV snapshot for a given date."""
    return get_item(_table(), pk=f"DATE#{date_str}", sk="PORTFOLIO")


def daily_run_already_completed(date_str: str) -> bool:
    """
    Idempotency check: has today's daily run already been persisted?
    The NAV item (SK=PORTFOLIO) is the last write in every daily run.
    """
    return item_exists(_table(), pk=f"DATE#{date_str}", sk="PORTFOLIO")
