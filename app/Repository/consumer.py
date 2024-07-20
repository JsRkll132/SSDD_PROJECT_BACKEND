# Conexión a RabbitMQ
import json
from ..Rabbitmq.rabbitmq import get_rabbitmq_connection
connection = get_rabbitmq_connection()
channel = connection.channel()
channel.queue_declare(queue='risk_validation_responses', durable=True)

STATUS_SCORE = None

def getStatusScore() : 
    return STATUS_SCORE

def callback(ch, method, properties, body):
    print("Received %r" % body)
    data = json.loads(body)
    queue_name = method.routing_key
    
    if queue_name == 'risk_validation_responses':
        STATUS_SCORE = data['risk']
        print(STATUS_SCORE)

    ch.basic_ack(delivery_tag=method.delivery_tag)

channel.basic_consume(queue='risk_validation_responses', on_message_callback=callback)

print('Esperando respuestas de validación de riesgo...')
channel.start_consuming()
