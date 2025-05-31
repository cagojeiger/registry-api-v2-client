"""Performance comparison between sync and async operations."""

import asyncio
import sys
import time

# Add parent directory to path
sys.path.insert(0, "src")

from registry_api_v2_client import list_repositories


async def async_multiple_calls(registry_url: str, num_calls: int = 5):
    """Make multiple async calls concurrently."""
    start_time = time.time()

    # Run multiple operations concurrently
    tasks = [list_repositories(registry_url) for _ in range(num_calls)]
    results = await asyncio.gather(*tasks)

    end_time = time.time()
    return end_time - start_time, len(results)


async def async_sequential_calls(registry_url: str, num_calls: int = 5):
    """Make multiple async calls sequentially."""
    start_time = time.time()

    results = []
    for _ in range(num_calls):
        result = await list_repositories(registry_url)
        results.append(result)

    end_time = time.time()
    return end_time - start_time, len(results)


async def main():
    """Performance comparison."""
    registry_url = "http://localhost:15000"
    num_calls = 5

    print(f"Performance Comparison: {num_calls} registry API calls")
    print("=" * 50)

    # Test concurrent async calls
    print("\n1. Concurrent Async Calls:")
    concurrent_time, concurrent_results = await async_multiple_calls(
        registry_url, num_calls
    )
    print(f"   Time: {concurrent_time:.2f} seconds")
    print(f"   Results: {concurrent_results} successful calls")
    print(f"   Rate: {concurrent_results / concurrent_time:.2f} calls/second")

    # Test sequential async calls
    print("\n2. Sequential Async Calls:")
    sequential_time, sequential_results = await async_sequential_calls(
        registry_url, num_calls
    )
    print(f"   Time: {sequential_time:.2f} seconds")
    print(f"   Results: {sequential_results} successful calls")
    print(f"   Rate: {sequential_results / sequential_time:.2f} calls/second")

    # Performance improvement
    if sequential_time > 0:
        improvement = (sequential_time - concurrent_time) / sequential_time * 100
        speedup = sequential_time / concurrent_time
        print("\n📈 Performance Improvement:")
        print(f"   Speedup: {speedup:.2f}x faster")
        print(f"   Time saved: {improvement:.1f}%")
        print(
            f"   Absolute time saved: {sequential_time - concurrent_time:.2f} seconds"
        )

    print(
        "\n🚀 Async concurrency allows multiple I/O operations to run simultaneously!"
    )
    print(
        "   This is especially beneficial for network-heavy operations like registry API calls."
    )


if __name__ == "__main__":
    asyncio.run(main())
