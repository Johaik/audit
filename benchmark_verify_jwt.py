import asyncio
import time
from typing import Dict, Any

# We need to test the verify_jwt function in a controlled environment
# So we mock the dependencies
class MockIdPProvider:
    def validate_token(self, token: str) -> Dict[str, Any]:
        # Simulate synchronous CPU-bound work (like jwt.decode) or I/O
        time.sleep(0.1)
        return {"tid": "test-tenant"}

# Import the function to test
from app.api.deps import verify_jwt

async def main():
    idp = MockIdPProvider()
    token = "fake-token"

    # Number of concurrent requests to simulate
    num_requests = 10

    print(f"Starting benchmark: {num_requests} concurrent token validations")
    start_time = time.perf_counter()

    # Create multiple concurrent tasks
    tasks = [verify_jwt(token=token, idp=idp) for _ in range(num_requests)]

    # Run them all concurrently
    await asyncio.gather(*tasks)

    end_time = time.perf_counter()
    duration = end_time - start_time

    print(f"Total time taken: {duration:.4f} seconds")
    print(f"Expected theoretical minimum time: 0.1000 seconds")
    print(f"Expected sequential time: {0.1 * num_requests:.4f} seconds")

    if duration > (0.1 * num_requests * 0.8):
        print("Result: Event loop was BLOCKED (executed sequentially)")
    else:
        print("Result: Event loop was NOT BLOCKED (executed concurrently)")

if __name__ == "__main__":
    asyncio.run(main())
