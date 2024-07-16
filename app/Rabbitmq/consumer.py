
import json

from rabbitmq import get_rabbitmq_connection
import requests
import ssl
import smtplib
from email.mime.text import MIMEText
from dotenv import load_dotenv
import os
RABBITMQ_QUEUES = ['order_confirmations', 'invoice_notifications','productos']
load_dotenv()

def send_email(cliente_email, orden):
    # Configura aquí los detalles del servidor SMTP y el remitente
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
    Tu Empresa
    '''
    
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = smtp_user
    msg['To'] = cliente_email

    with smtplib.SMTP_SSL(smtp_server, smtp_port,context=context) as server:
        server.login(smtp_user, smtp_password)
        server.sendmail(smtp_user,cliente_email,msg.as_string())

def callback(ch, method, properties, body):
    print("Received %r" % body)
    data = json.loads(body)
    queue_name  =  method.routing_key
    if (queue_name == 'productos') : 
        print(f"Procesando tarea para producto_id: {data['producto_id']}")
    elif (queue_name == 'order_confirmations') : 
        orden_id =data['orden_id']
        cliente_email = data['cliente_email']
        
        # Realizar solicitud al microservicio para obtener la orden
        response = requests.get('http://127.0.0.1:5000/api/ordenes/'+ str(orden_id))
        
        if response.status_code == 200:
            orden_data = response.json()
            
            if orden_data['status'] == 1:
                orden = orden_data['orden']
                # Enviar el correo electrónico con los detalles de la factura
                send_email(cliente_email, orden)
            else:
                print(f'Error: {orden_data["error"]}')
        else:
            print(f'Error al obtener la orden: {response.status_code}')


        pass
    # Aquí puedes realizar tareas adicionales
    # Por ejemplo, enviar una notificación, actualizar caché, etc.
    

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
