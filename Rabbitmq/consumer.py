import json
import requests
import ssl
import smtplib
from email.mime.text import MIMEText
from dotenv import load_dotenv
import os
import pika
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Usuario,Base
from rabbitmq import get_rabbitmq_connection
from models_equifax import Base as equifax_base
from models_equifax import Cliente

# Configuración de RabbitMQ
RABBITMQ_QUEUES = ['order_confirmations', 'invoice_notifications', 'productos', 'credito_carga','validar_riesgo']

load_dotenv()

# Configuración de SQLAlchemy
DATABASE_URL = os.getenv('DATABASE_URL')
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
session = Session()


DATABASE_URL_EQUIFAX = os.getenv('DATABASE_URL_EQUIFAX')
Session_equifax = sessionmaker(bind = create_engine(DATABASE_URL_EQUIFAX))
session_equifax = Session_equifax()


def publish_message(queue_name, message):
    connection = get_rabbitmq_connection()
    channel = connection.channel()
    channel.queue_declare(queue=queue_name, durable=True)
    
    channel.basic_publish(
        exchange='',
        routing_key=queue_name,
        body=json.dumps(message),
        properties=pika.BasicProperties(
            delivery_mode=2,  # Mensaje persistente
        ))
    connection.close()
def verief_credir(username, order_id):
    try:
        cliente = session_equifax.query(Cliente).filter_by(nombre_usuario=username).first()
        if cliente:
            response = {
                'username': username,
                'order_id': order_id,
                'risk': cliente.riesgo
            }
            return response
        else:
            return None
    except Exception as e:
        session_equifax.rollback()
        raise e

def send_email(cliente_email, orden):
    smtp_server = 'smtp.gmail.com'
    smtp_port = 465
    smtp_user = os.getenv('EMAIL_SENDER')
    smtp_password = os.getenv('EMAIL_PASSWORD')
    
    subject = f'Factura #{orden["id"]}'
    body = f'''
    Estimado Cliente,

    Gracias por su compra. Aquí están los detalles de su factura:

    - Número de Orden: {orden["id"]}
    - Estado: {orden["estado"]}
    - Fecha de Creación: {orden["fecha_creacion"]}

    Detalles de los productos comprados:
    '''
    
    for detalle in orden['detalles']:
        body += f'''
        - Producto: {detalle['nombre_producto']}
          Cantidad: {detalle['cantidad']}
          Precio unitario: {detalle['precio_compra']}
          Precio total: {detalle['precio_compra'] * detalle['cantidad']}
        '''
    context = ssl.create_default_context()
    body += '''
    Atentamente,
    Grupo Deltron
    '''
    
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = smtp_user
    msg['To'] = cliente_email

    with smtplib.SMTP_SSL(smtp_server, smtp_port,context=context) as server:
        server.login(smtp_user, smtp_password)
        server.sendmail(smtp_user,cliente_email,msg.as_string())

def update_credito(user_id, amount):
    try:
        usuario = session.query(Usuario).filter_by(id=user_id).first()
        if usuario:
            usuario.credito += amount
            session.commit()
            print(f"Crédito de usuario {user_id} actualizado a {usuario.credito}")
        else:
            print(f"Usuario {user_id} no encontrado")
    except Exception as e:
        session.rollback()
        print(f"Error al actualizar el crédito: {str(e)}")

def callback(ch, method, properties, body):
    print("Received %r" % body)
    data = json.loads(body)
    queue_name = method.routing_key
    
    if queue_name == 'productos':
        print(f"Procesando tarea para producto_id: {data['producto_id']}")
    elif queue_name == 'order_confirmations':
        orden_id = data['orden_id']
        cliente_email = data['cliente_email']
        response = requests.get('http://127.0.0.1:5000/api/ordenes/' + str(orden_id))
        
        if response.status_code == 200:
            orden_data = response.json()
            if orden_data['status'] == 1:
                orden = orden_data['orden']
                send_email(cliente_email, orden)
            else:
                print(f'Error: {orden_data["error"]}')
        else:
            print(f'Error al obtener la orden: {response.status_code}')
    elif queue_name == 'credito_carga':
        user_id = data['user_id']
        amount = data['amount']
        update_credito(user_id, amount)
    elif queue_name == 'validar_riesgo':
        username = data['username']
        order_id = data['orden_id']
        response = verief_credir(username, order_id)

        if response:
            ch.basic_publish(
                exchange='',
                routing_key=properties.reply_to,
                properties=pika.BasicProperties(
                    correlation_id=properties.correlation_id
                ),
                body=json.dumps(response)
            )
    ch.basic_ack(delivery_tag=method.delivery_tag)



def start_consumer():
    try:
        connection = get_rabbitmq_connection()
        channel = connection.channel()

        for queue in RABBITMQ_QUEUES:
            channel.queue_declare(queue=queue, durable=True)
            channel.basic_qos(prefetch_count=1)
            channel.basic_consume(queue=queue, on_message_callback=callback)

        print('Esperando mensajes. Para salir presione CTRL+C')
        channel.start_consuming()
    except Exception as e:
        print(f"Error in start_consumer: {str(e)}")




if __name__ == '__main__':
    start_consumer()
