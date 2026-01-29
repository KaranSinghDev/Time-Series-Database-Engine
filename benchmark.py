import ctypes
import os
import time
import random
import shutil
import numpy as np
import json
from kafka import KafkaProducer, errors

# --- ============================== ---
# --- Part 1: C++ Engine Configuration ---
# --- ============================== ---
DATA_DIRECTORY = "data"
NUM_POINTS_ENGINE = 100_000
NUM_QUERIES_ENGINE = 100

# --- C++ Bridge Setup ---
class CDataPoint(ctypes.Structure):
    _fields_ = [("timestamp", ctypes.c_uint64), ("value", ctypes.c_double)]

# --- ============================== ---
# --- Part 2: Kafka Pipeline Configuration ---
# --- ============================== ---
KAFKA_TOPIC = 'raw-metrics'
KAFKA_NUM_MESSAGES = 1_000_000
KAFKA_BOOTSTRAP_SERVER = 'localhost:9092'


# --- ============================== ---
# --- Part 3: Benchmark Functions ---
# --- ============================== ---

# --- C++ ENGINE BENCHMARKS ---

def run_ingestion_benchmark(lib):
    """Benchmarks the C++ engine's point-by-point file I/O ingestion."""
    print(f"\n--- C++ Engine: Ingestion Benchmark ({NUM_POINTS_ENGINE:,} points) ---")
    points_to_ingest = []
    start_ts = int(time.time() * 1000)
    for i in range(NUM_POINTS_ENGINE):
        timestamp = start_ts + (i * 1000)
        value = 50.0 + 20.0 * (np.sin(i / 100.0)) + random.uniform(-1.0, 1.0)
        points_to_ingest.append((timestamp, value))

    start_time = time.perf_counter()
    for ts, val in points_to_ingest:
        lib.ingest_point(ts, val)
    end_time = time.perf_counter()

    duration_s = end_time - start_time
    points_per_second = NUM_POINTS_ENGINE / duration_s
    print(f"RESULT: Ingested {NUM_POINTS_ENGINE:,} points in {duration_s:.2f} seconds.")
    print(f"  => C++ Engine Throughput: {points_per_second:,.0f} points/sec")
    return points_to_ingest

def run_storage_benchmark():
    """Benchmarks the C++ engine's on-disk compression ratio."""
    print(f"\n--- C++ Engine: Storage Efficiency Benchmark ---")
    uncompressed_size = NUM_POINTS_ENGINE * 16
    compressed_size = sum(f.stat().st_size for f in os.scandir(DATA_DIRECTORY) if f.is_file())
    bytes_per_point = compressed_size / NUM_POINTS_ENGINE
    compression_ratio = uncompressed_size / compressed_size
    print(f"RESULT: On-disk size for {NUM_POINTS_ENGINE:,} points is {compressed_size / (1024*1024):.2f} MB.")
    print(f"  => Average Bytes per Point: {bytes_per_point:.2f}")
    print(f"  => Compression Ratio: {compression_ratio:.1f}x")

def run_query_benchmark(lib, all_points):
    """Benchmarks the C++ engine's hot and cold query latency."""
    print(f"\n--- C++ Engine: Query Latency Benchmark ({NUM_QUERIES_ENGINE} queries) ---")
    BUFFER_CAPACITY = 1_000_000
    BufferArrayType = CDataPoint * BUFFER_CAPACITY
    result_buffer = BufferArrayType()
    
    # Short-range, "hot" data query
    hot_latencies = []
    for _ in range(NUM_QUERIES_ENGINE):
        start_index = random.randint(int(NUM_POINTS_ENGINE * 0.9), NUM_POINTS_ENGINE - 3601)
        query_start_ts = all_points[start_index][0]
        query_end_ts = query_start_ts + (3600 * 1000)
        start_time = time.perf_counter()
        lib.query_range(query_start_ts, query_end_ts, result_buffer, BUFFER_CAPACITY)
        end_time = time.perf_counter()
        hot_latencies.append((end_time - start_time) * 1000)
    
    # Long-range, "cold" data query
    cold_latencies = []
    for _ in range(NUM_QUERIES_ENGINE):
        start_index = random.randint(0, int(NUM_POINTS_ENGINE * 0.5) - 86401)
        query_start_ts = all_points[start_index][0]
        query_end_ts = query_start_ts + (24 * 3600 * 1000)
        start_time = time.perf_counter()
        lib.query_range(query_start_ts, query_end_ts, result_buffer, BUFFER_CAPACITY)
        end_time = time.perf_counter()
        cold_latencies.append((end_time - start_time) * 1000)

    print_stats("Short-range Query (1 hour, 'hot' data)", hot_latencies)
    print_stats("Long-range Query (24 hours, 'cold' data)", cold_latencies)

def print_stats(label, latencies_ms):
    """Helper function to print latency statistics."""
    p99 = np.percentile(latencies_ms, 99)
    avg = np.mean(latencies_ms)
    print(f"  - {label}: p99: {p99:.2f} ms, avg: {avg:.2f} ms")

def run_full_engine_suite():
    """Orchestrates the complete C++ engine benchmark suite."""
    print("\n" + "="*60)
    print("  Running Full C++ Engine Benchmark Suite")
    print("="*60)
    
    try:
        lib_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "engine", "build", "libinsight.so")
        lib = ctypes.CDLL(lib_path)
        
        # Define function signatures
        lib.ingest_point.argtypes = [ctypes.c_uint64, ctypes.c_double]
        lib.ingest_point.restype = None
        lib.query_range.argtypes = [ctypes.c_uint64, ctypes.c_uint64, ctypes.POINTER(CDataPoint), ctypes.c_int64]
        lib.query_range.restype = ctypes.c_int64
    except OSError:
        print(f"\nFATAL: Could not load C++ library at {lib_path}")
        print("Please ensure the engine is compiled ('cmake --build build' in 'engine/' directory).")
        return

    if os.path.exists(DATA_DIRECTORY):
        shutil.rmtree(DATA_DIRECTORY)
        
    ingested_points = run_ingestion_benchmark(lib)
    run_storage_benchmark()
    run_query_benchmark(lib, all_points=ingested_points)
    
    if os.path.exists(DATA_DIRECTORY):
        shutil.rmtree(DATA_DIRECTORY)
    print("\nC++ Engine benchmark complete.")

# --- KAFKA PIPELINE BENCHMARK ---

# --- KAFKA PIPELINE BENCHMARK ---

# NEW helper function for multiprocessing
def kafka_producer_worker(num_messages_per_worker, bootstrap_server, topic):
    """A single producer process that sends a batch of messages."""
    producer = KafkaProducer(
        bootstrap_servers=bootstrap_server,
        acks=1,
        compression_type='lz4',
        linger_ms=0,
        batch_size=128 * 1024
    )
    payload_dict = {"sensor_id":"b_test","timestamp":1,"payload_bytes":2,"status":"COMP"}
    serialized_payload = json.dumps(payload_dict).encode('utf-8')

    for _ in range(num_messages_per_worker):
        producer.send(topic, serialized_payload)
    
    producer.flush()

# REPLACED function
def run_kafka_benchmark_high_throughput():
    """Benchmarks the Kafka pipeline's maximum ingestion throughput using multiple processes."""
    print("\n" + "="*60)
    print(f"  Running Kafka Ingestion Stress Test (MULTIPROCESS) ({KAFKA_NUM_MESSAGES:,} messages)")
    print("="*60)
    
    # Use multiprocessing to run producers in parallel, bypassing the Python GIL
    # We'll use half the available CPU cores to not overload the system
    import multiprocessing
    num_workers = multiprocessing.cpu_count() // 2
    if num_workers < 1:
        num_workers = 1
    
    messages_per_worker = KAFKA_NUM_MESSAGES // num_workers

    print(f"Starting {num_workers} parallel producer workers...")

    start_time = time.time()
    
    processes = []
    for _ in range(num_workers):
        p = multiprocessing.Process(
            target=kafka_producer_worker,
            args=(messages_per_worker, KAFKA_BOOTSTRAP_SERVER, KAFKA_TOPIC)
        )
        processes.append(p)
        p.start()
        
    for p in processes:
        p.join() # Wait for all producer processes to finish

    end_time = time.time()
    
    duration = end_time - start_time
    # We calculate throughput based on the total messages sent by all workers
    total_messages = messages_per_worker * num_workers
    throughput = total_messages / duration

    print(f"\nRESULT: Sent {total_messages:,} messages in {duration:.2f} seconds.")
    print(f"  => Kafka Pipeline Throughput: {throughput:,.0f} ops/sec")
    print("\nKafka benchmark complete.")
# --- ============================== ---
# --- Part 4: Main Interactive Menu ---
# --- ============================== ---

def main():
    """Presents an interactive menu to the user."""
    while True:
        print("\n" + "="*50)
        print("        Insight-TSDB Benchmark Utility")
        print("="*50)
        print("1. Run Full C++ Engine Benchmark Suite (Ingest, Storage, Query)")
        print("2. Run Kafka Pipeline Ingestion Benchmark (High Throughput)")
        print("3. Run ALL Benchmarks")
        print("4. Exit")
        
        choice = input("Enter your choice [1-4]: ")
        
        if choice == '1':
            run_full_engine_suite()
        elif choice == '2':
            run_kafka_benchmark_high_throughput()
        elif choice == '3':
            run_full_engine_suite()
            run_kafka_benchmark_high_throughput()
        elif choice == '4' or choice.lower() == 'q':
            print("Exiting.")
            break
        else:
            print("Invalid choice. Please try again.")

if __name__ == "__main__":
    main()