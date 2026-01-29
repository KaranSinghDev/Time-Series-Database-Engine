from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col, when
from pyspark.sql.types import StructType, StructField, DoubleType, IntegerType, StringType

# 1. Initialize Spark
spark = SparkSession.builder \
    .appName("CompressionAnomalyDetector") \
    .getOrCreate()

# 2. Define Schema (Must match producer.py)
schema = StructType([
    StructField("sensor_id", StringType()),
    StructField("timestamp", DoubleType()),
    StructField("payload_bytes", IntegerType()),
    StructField("status", StringType())
])

# 3. READ STREAM from Kafka
# We read from the 'raw-metrics' topic
raw_stream = spark.readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", "kafka:29092") \
    .option("subscribe", "raw-metrics") \
    .option("startingOffsets", "latest") \
    .load()

# 4. PARSE the JSON data
# Kafka sends data as binary bytes in the 'value' column. We cast to string and parse JSON.
parsed_stream = raw_stream.select(
    from_json(col("value").cast("string"), schema).alias("data")
).select("data.*")

# 5. ANALYTIC LOGIC: Detect Anomalies
# Condition: If payload_bytes > 10, it implies compression failed (expected 2 bytes).
analyzed_stream = parsed_stream.withColumn(
    "alert_message", 
    when(col("payload_bytes") > 10, "CRITICAL: Compression Ratio Drop Detected! (Uncompressed Data Found)")
    .otherwise(None)
)

# 6. FILTER: Keep only the anomalies
alerts = analyzed_stream.filter(col("alert_message").isNotNull())

# 7. FORMAT FOR KAFKA
# Kafka needs a 'key' and a 'value'.
kafka_output = alerts.select(
    col("sensor_id").alias("key"),
    col("alert_message").alias("value")
)

# 8. WRITE STREAM back to Kafka ('compression-alerts')
print(">>> Starting Streaming Query...")
query = kafka_output.writeStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", "kafka:29092") \
    .option("topic", "compression-alerts") \
    .option("checkpointLocation", "/tmp/checkpoints") \
    .start()

query.awaitTermination()