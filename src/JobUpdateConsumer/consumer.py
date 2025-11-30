
import signal
import sys
from confluent_kafka import Consumer

running = True

def handle_sigterm(signum, frame):
    global running
    print("Received stop signal, shutting down gracefully...")
    running = False

signal.signal(signal.SIGINT, handle_sigterm)
signal.signal(signal.SIGTERM, handle_sigterm)

conf = {
    'bootstrap.servers': 'kafka:29092',
    'group.id': 'job-update-consumer',
    'auto.offset.reset': 'earliest'
}

consumer = Consumer(conf)
consumer.subscribe(['my_topic'])  # Đổi 'my_topic' thành topic bạn muốn
print("Consumer started, waiting for messages...")
try:
    while running:
        msg = consumer.poll(1.0)
        if msg is None:
            continue
        if msg.error():
            print(f"Consumer error: {msg.error()}")
            continue
        print(f"Received: {msg.value().decode('utf-8')}")
finally:
    consumer.close()
    print("Consumer closed gracefully.")
    sys.exit(0)