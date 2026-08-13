"""Unit tests for core module."""

from __future__ import annotations

import pytest

from core import DataProcessor, ProcessorConfig


def test_processor_initialization(default_processor: DataProcessor) -> None:
    """Test DataProcessor initialization state."""
    assert default_processor.config.batch_size == 50
    assert default_processor.processed_count == 0


def test_process_item_success(default_processor: DataProcessor) -> None:
    """Test process_item with valid input dictionary."""
    item = {"id": "test_1", "value": 42}
    result = default_processor.process_item(item)
    assert result["processed"] is True
    assert result["batch_size"] == 50
    assert default_processor.processed_count == 1


def test_process_item_strict_validation_failure() -> None:
    """Test process_item raises ValueError when missing 'id' in strict mode."""
    processor = DataProcessor(ProcessorConfig(strict_mode=True))
    with pytest.raises(ValueError, match="Payload missing required 'id' key"):
        processor.process_item({"value": 100})


def test_process_batch(default_processor: DataProcessor) -> None:
    """Test process_batch with list of items."""
    items = [{"id": f"item_{i}", "val": i} for i in range(5)]
    results = default_processor.process_batch(items)
    assert len(results) == 5
    assert default_processor.processed_count == 5
