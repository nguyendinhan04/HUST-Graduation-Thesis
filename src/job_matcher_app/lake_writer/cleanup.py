from __future__ import annotations

import logging
from typing import Any

from job_matcher_app.event_outbox import delete_exported_event_outboxes
from job_matcher_app.lake_writer.settings import LakeWriterSettings


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def cleanup_exported_event_outbox(
    retention_days: int | None = None,
    limit: int | None = None,
) -> dict[str, Any]:
    settings = LakeWriterSettings()
    retention = retention_days or settings.event_outbox_retention_days
    delete_limit = limit or settings.event_outbox_cleanup_batch_size
    deleted = delete_exported_event_outboxes(retention, delete_limit)
    logger.info(
        "Deleted %s exported outbox rows with retention_days=%s limit=%s",
        deleted,
        retention,
        delete_limit,
    )
    return {
        "deleted": deleted,
        "retention_days": retention,
        "limit": delete_limit,
    }


def main() -> None:
    cleanup_exported_event_outbox()


if __name__ == "__main__":
    main()
