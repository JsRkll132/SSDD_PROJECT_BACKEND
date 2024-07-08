
import json

from rabbitmq import get_rabbitmq_connection

def callback(ch, method, properties, body):
    print("Received %r" % body)
    data = json.loads(body)
    
    # Aquí puedes realizar tareas adicionales
    # Por ejemplo, enviar una notificación, actualizar caché, etc.
    print(f"Procesando tarea para producto_id: {data['producto_id']}")

    ch.basic_ack(delivery_tag=method.delivery_tag)

def start_consumer():
    try:
        connection = get_rabbitmq_connection()
        channel = connection.channel()

        channel.queue_declare(queue='productos', durable=True)

        channel.basic_qos(prefetch_count=1)
        channel.basic_consume(queue='productos', on_message_callback=callback)

        print('Waiting for messages. To exit press CTRL+C')
        channel.start_consuming()
    except Exception as e:
        print(f"Error in start_consumer: {str(e)}")

if __name__ == '__main__':
    start_consumer()
