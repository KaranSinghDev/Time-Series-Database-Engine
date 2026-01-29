import time
import json
import random
from kafka import KafkaProducer

# Connect to Kafka running on localhost
producer = KafkaProducer(
    bootstrap_servers='localhost:9092',
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

TOPIC = 'raw-metrics'

print(f"🚀 Producer started. Sending data to '{TOPIC}'...")
print("   - Simulating C++ Engine output")
print("   - Normal (Compressed): ~2 bytes")
print("   - Anomaly (Uncompressed): ~16 bytes")

try:
    while True:
        timestamp = time.time()
        
        # 90% chance of normal compressed data (Delta-of-Delta)
        if random.random() > 0.1:
            # Simulate a small delta (2 bytes)
            payload_size = 2
            status = "COMPRESSED"
        else:
            # 10% chance of anomaly (Raw uncompressed double + timestamp)
            payload_size = 16 
            status = "UNCOMPRESSED_FAILURE"

        data = {
            "sensor_id": "sensor_01",
            "timestamp": timestamp,
            "payload_bytes": payload_size,
            "status": status
        }

        producer.send(TOPIC, data)
        
        # Visual feedback in console
        if status == "UNCOMPRESSED_FAILURE":
            print(f"⚠️  [ANOMALY SENT] Size: {payload_size} bytes")
        else:
            print(f"   [Normal] Size: {payload_size} bytes", end='\r')

        time.sleep(0.5) # Send 2 points per second

except KeyboardInterrupt:
    print("\nStopping producer...")
    producer.close()
