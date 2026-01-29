from kafka import KafkaConsumer

TOPIC = 'compression-alerts'

print(f"📡 Monitoring '{TOPIC}' for system alerts...")

consumer = KafkaConsumer(
    TOPIC,
    bootstrap_servers='localhost:9092',
    # CHANGE 1: Read from the start of history so we don't miss anything
    auto_offset_reset='earliest', 
    # CHANGE 2: Disable consumer groups so we always get all messages (good for debugging)
    group_id=None 
)

for msg in consumer:
    print(f"🚨 ALERT RECEIVED: {msg.value.decode('utf-8')}")