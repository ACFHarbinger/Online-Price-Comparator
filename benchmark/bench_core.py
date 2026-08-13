"""Performance benchmarks for core module."""

import time

from core import DataProcessor, ProcessorConfig


def run_benchmark() -> None:
    processor = DataProcessor(ProcessorConfig(batch_size=1000, strict_mode=False))
    items = [{"id": f"item_{i}", "val": i} for i in range(10000)]

    start = time.perf_counter()
    processor.process_batch(items)
    elapsed = time.perf_counter() - start

    rate = len(items) / elapsed
    print(f"Benchmark: Processed {len(items)} items in {elapsed:.4f}s")
    print(f"Throughput: {rate:.2f} ops/s")


if __name__ == "__main__":
    run_benchmark()
