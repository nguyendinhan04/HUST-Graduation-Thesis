import confluent_kafka
import json

# push messsage to kafka topic
def produce_message(topic, message):
    conf = {
        'bootstrap.servers': 'localhost:9092'
    }
    producer = confluent_kafka.Producer(conf)
    producer.produce(topic, message)
    producer.flush()
if __name__ == "__main__":
    test_topic = "job-updates"

    data = {
            "url_hash": r"5deee34b69985e34e4da41b8add861fb896be45c93fac56f1f99eca63a1c2487",
            "job_url": r"https://www.topcv.vn/viec-lam/tester-game/1962969.html",
            "title": "Tester Game"
        }


    test_message = json.dumps(data)
    produce_message(test_topic, test_message)
    print(f"Produced test message to topic '{test_topic}'")
