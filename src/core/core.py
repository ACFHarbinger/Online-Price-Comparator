"""Core data processing engine for Python-Module-Template."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ProcessorConfig:
    """Configuration parameters for DataProcessor.

    Attributes:
        batch_size: Number of items per batch execution.
        strict_mode: Enable strict validation checks.
        metadata: Additional processing key-value attributes.
    """

    batch_size: int = 100
    strict_mode: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)


class DataProcessor:
    """Core processing engine responsible for pipeline transformations."""

    def __init__(self, config: ProcessorConfig | None = None) -> None:
        """Initialize the DataProcessor instance.

        Args:
            config: Optional ProcessorConfig settings object.
        """
        self.config = config or ProcessorConfig()
        self._processed_count: int = 0

    @property
    def processed_count(self) -> int:
        """Total count of processed elements."""
        return self._processed_count

    def process_item(self, item: dict[str, Any]) -> dict[str, Any]:
        """Process a single data item dictionary.

        Args:
            item: Input dictionary payload.

        Returns:
            Transformed data dictionary payload.

        Raises:
            ValueError: If strict_mode is enabled and required payload keys are missing.
        """
        if self.config.strict_mode and "id" not in item:
            raise ValueError("Payload missing required 'id' key in strict mode")

        processed = dict(item)
        processed["processed"] = True
        processed["batch_size"] = self.config.batch_size
        self._processed_count += 1
        return processed

    def process_batch(self, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Process a list of data items.

        Args:
            items: List of input dictionaries.

        Returns:
            List of processed dictionaries.
        """
        return [self.process_item(item) for item in items]
