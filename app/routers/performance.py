import time
from fastapi import APIRouter

router = APIRouter(prefix="/api/performance", tags=["Performance Testing"])

@router.get("/benchmark")
def run_benchmark_test(iterations: int = 100):
    start_time = time.time()
    counter = 0
    for i in range(iterations):
        counter += (i * 2)
    duration = time.time() - start_time
    
    return {
        "status": "PASS",
        "iterations": iterations,
        "execution_time_seconds": round(duration, 6),
        "throughput_ops_per_sec": round(iterations / duration if duration > 0 else 1000000, 2),
        "result_sample": counter
    }
