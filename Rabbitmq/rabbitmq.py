import pika
import os

def get_rabbitmq_connection():
    credentials = pika.PlainCredentials('guest', 'guest')
    parameters = pika.ConnectionParameters('localhost', 5672, '/', credentials)

    try:
        connection = pika.BlockingConnection(parameters)
        print("Successfully connected to RabbitMQ")
        return connection
    except Exception as e:
        print(f"Error connecting to RabbitMQ: {str(e)}")
        return None