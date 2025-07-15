import os, time, json, random
from datetime import datetime
from kafka import KafkaProducer
from kafka.errors import NoBrokersAvailable

BROKER = os.getenv("KAFKA_BROKER", "kafka:9092")
TOPIC  = os.getenv("KAFKA_TOPIC",  "world_population")

BASE_POP = 8_200_000_000
BIRTHS_PER_SEC = 4.3
DEATHS_PER_SEC = 1.8

# Retry logic for Kafka
for attempt in range(10):
    try:
        producer = KafkaProducer(
            bootstrap_servers=BROKER,
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )
        print(f"✅ Connected to Kafka broker at {BROKER}")
        break
    except NoBrokersAvailable:
        print(f"❌ Kafka not ready, retrying in 5s... ({attempt+1}/10)")
        time.sleep(5)
else:
    raise Exception("Failed to connect to Kafka after retries")

time.sleep(3)

pop = BASE_POP
births_today = deaths_today = 0
births_this_year = deaths_this_year = 0
growth_this_year = 0
growth_today = 0

print(f"📤 Streaming to topic '{TOPIC}'")

while True:
    births = max(0, int(random.gauss(BIRTHS_PER_SEC, 0.5)))
    deaths = max(0, int(random.gauss(DEATHS_PER_SEC, 0.3)))
    growth = births - deaths

    pop += growth
    births_today += births
    deaths_today += deaths
    births_this_year += births
    deaths_this_year += deaths
    growth_this_year += growth
    growth_today += growth

    payload = {
        "timestamp": datetime.utcnow().isoformat(),
        "population": pop,
        "births_today": births_today,
        "births_this_year": births_this_year,
        "deaths_today": deaths_today,
        "deaths_this_year": deaths_this_year,
        "growth_today": growth_today,
        "growth_this_year": growth_this_year
    }

    print("📦", payload)
    producer.send(TOPIC, payload)
    producer.flush()

    now = datetime.utcnow()
    if now.hour == 0 and now.minute == 0 and now.second < 2:
        births_today = deaths_today = growth_today =  0
    if now.month == 1 and now.day == 1 and now.hour == 0:
        births_this_year = deaths_this_year = growth_this_year = 0

    time.sleep(1)
