"""Shared pytest fixtures for Python-Module-Template test suite."""

import pytest

from core import DataProcessor, ProcessorConfig


@pytest.fixture
def default_config() -> ProcessorConfig:
    """Fixture providing default ProcessorConfig instance."""
    return ProcessorConfig(batch_size=50, strict_mode=True)


@pytest.fixture
def default_processor(default_config: ProcessorConfig) -> DataProcessor:
    """Fixture providing DataProcessor instance configured with default settings."""
    return DataProcessor(default_config)
