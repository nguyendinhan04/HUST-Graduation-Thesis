from confluent_kafka import Producer
import socket

class KafkaProducerClass:
    def __init__(self):
        self.conf = {
            'bootstrap.servers': 'kafka:29092',
            'client.id': socket.gethostname()
        }
        self.producer = Producer(self.conf)

    def send_message(self, topic: str, message: str):
        def delivery_report(err, msg):
            """ Called once for each message produced to indicate delivery result.
                Triggered by poll() or flush(). """
            if err is not None:
                print('Message delivery failed: {}'.format(err))
            else:
                # print('Message delivered to {} [{}]'.format(msg.topic(), msg.partition()))
                pass

        self.producer.poll(0)
        self.producer.produce(topic, message.encode('utf-8'), callback=delivery_report)
        self.producer.flush()

    def close(self):
        self.producer.flush()