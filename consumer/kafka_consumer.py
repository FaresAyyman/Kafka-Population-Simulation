import psycopg2
from kafka import KafkaConsumer
import json
import time
from datetime import datetime

# Wait for Kafka broker to become available
for i in range(10):
    try:
        consumer = KafkaConsumer(
            'world_population',
            bootstrap_servers='kafka:9092',
            value_deserializer=lambda v: json.loads(v.decode('utf-8')),
            auto_offset_reset='earliest',   # read from earliest if no committed offset
            enable_auto_commit=True,
            group_id='world-pop-consumer'
        )
        print("Connected to Kafka")
        break
    except Exception as e:
        print(f"Kafka not ready, retrying in 5s... ({i+1}/10)")
        time.sleep(5)
else:
    raise Exception("Failed to connect to Kafka after retries")

# Give some time before starting consumption
time.sleep(5)

# Connect to PostgreSQL
conn = psycopg2.connect(
    dbname="population",
    user="kafkauser",
    password="kafkapass",
    host="postgres"
)
cur = conn.cursor()

# Create the table if it doesn't exist
cur.execute("""
CREATE TABLE IF NOT EXISTS population_snapshot (
    id SERIAL PRIMARY KEY,
    ts TIMESTAMP,
    population BIGINT,
    births_today BIGINT,
    births_this_year BIGINT,
    deaths_today BIGINT,
    deaths_this_year BIGINT,
    growth_today BIGINT,
    growth_this_year BIGINT
);
""")
conn.commit()

print("Starting to consume messages and insert into DB...")

commit_every = 10
count = 0

for msg in consumer:
    data = msg.value
    print("Received:", data)

    try:
        ts = datetime.fromisoformat(data['timestamp'])
        cur.execute("""
            INSERT INTO population_snapshot (
                ts, population,
                births_today, births_this_year,
                deaths_today, deaths_this_year,
                growth_today, growth_this_year
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
        """, (
            ts,
            data['population'],
            data['births_today'],
            data['births_this_year'],
            data['deaths_today'],
            data['deaths_this_year'],
            data['growth_today'],
            data['growth_this_year']
        ))
        count += 1
        if count % commit_every == 0:
            conn.commit()
    except Exception as e:
        print(f"Error inserting data: {e}")

# Final commit for any leftover inserts (if script is stopped gracefully)
conn.commit()