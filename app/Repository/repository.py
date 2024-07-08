import json
import pika
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.Rabbitmq.rabbitmq import get_rabbitmq_connection
from ..Models.models import Reserva, Usuario,Producto,Factura,Orden,ItemOrden,Rol
import os


engine = create_engine(os.getenv('DATABASE_URL'))
Session = sessionmaker(bind=engine)
session = Session()


def getRoles() : 
    try : 
        roles = session.query(Rol).all()
        data_roles = [{'id':rol.id,'nombre':rol.nombre} for rol in roles]
        return data_roles
    except Exception as e : 
        session.rollback()
        print('*'*40+str(e)+'*'*40)
        return None
        
def listar_productos():
    try : 
        productos = session .query(Producto).all()
        resultado = [{'id': p.id, 'nombre': p.nombre, 'precio': p.precio, 'sku': p.sku, 'stock': p.stock, 'url_imagen': p.url_imagen} for p in productos]
        return resultado
    except : 
        session.rollback()
        return None
    
def generar_orden(client_id,items) : 
    try :
        nueva_orden = Orden(cliente_id=client_id, estado='Pendiente')
        session.add(nueva_orden)
        session.commit()
        for item in items:
            producto_id = item['producto_id']
            cantidad = item['cantidad']
            producto = session.query(Producto).get(producto_id)
            if producto and producto.stock >= cantidad:
                item_orden = ItemOrden(
                    orden_id=nueva_orden.id,
                    producto_id=producto_id,
                    cantidad=cantidad,
                    precio_compra=producto.precio
                )
                producto.stock -= cantidad
                session.add(item_orden)
            else:
                return {'error': 'Producto no disponible o stock insuficiente'}
        session.commit()
        return {'message': 'Orden generada con éxito', 'orden_id': nueva_orden.id}
    except : 
        session.rollback()
        return None


def pagarRepository(orden_id,metodo):
    try :
        orden = session.query(Orden).get(orden_id)
        if not orden:
            return {'error': 'Orden no encontrada'}

        monto_total = sum(item.cantidad * item.precio_compra for item in orden.items)
        nueva_factura = Factura(orden_id=orden_id, monto=monto_total, pagada=True)
        session.add(nueva_factura)
        session.commit()
        return {'message': 'Pago realizado con éxito', 'factura_id': nueva_factura.id}
    except Exception as e :
        session.rollback()
        print(str(e))
        return {'error': 'Error en la operacion'}

def confirmar_ordenRepository(orden_id) : 
    try :
        orden = session.query(Orden).get(orden_id)
        if not orden:
            return {'error': 'Orden no encontrada'}

        orden.estado = 'Confirmada'
        reserva = Reserva(orden_id=orden_id)
        session.add(reserva)
        session.commit()

        return {'message': 'Orden confirmada y reservada con éxito'}
    except Exception as e :
        session.rollback()
        print(str(e))
        return {'error': 'Error en la operacion'}
    

def verificar_scoreRepository(cliente_id) : 
    try : 
        cliente = session.query(Usuario).get(cliente_id)
        if not cliente:
            return {'error': 'Cliente no encontrado'}

        score = cliente.score_crediticio
        if score >= 600:
            return {'status':1,'message': 'Crédito aprobado', 'score': score}
        else:
            return {'status':0,'message': 'Crédito rechazado', 'score': score}
    except Exception as e :
        print(str(e))
        session.rollback()
        return None
    
def facturas_pendientesRepository():
    try : 
        facturas = session.query(Factura).filter_by(pagada=False).all()
        resultado = [{'id': f.id, 'orden_id': f.orden_id, 'monto': f.monto, 'fecha_emision': f.fecha_emision} for f in facturas]
        return resultado
    except Exception as e : 
        print(str(e))
        session.rollback()
        return None
    
def confirmar_pagoRepository(factura_id) : 
    try :
        
        factura = session.query(Factura).get(factura_id)
        if not factura:
            return {'error': 'Factura no encontrada'}

        factura.pagada = True
        session.commit()

        return {'message': 'Pago confirmado'}
    except :
        session.rollback()
        return None
        
def agregar_productoRepository(data) :
    try :
        nuevo_producto = Producto(
            nombre=data['nombre'],
            precio=data['precio'],
            sku=data['sku'],
            stock=data['stock'],
            url_imagen=data['url_imagen']
        )
        session.add(nuevo_producto)
        session.commit()
        # Después de agregar el producto, envía un mensaje a RabbitMQ
        connection = get_rabbitmq_connection()
        channel = connection.channel()
        channel.queue_declare(queue='productos', durable=True)
        
        message = json.dumps({'producto_id': nuevo_producto.id})
        channel.basic_publish(
            exchange='',
            routing_key='productos',
            body=message,
            properties=pika.BasicProperties(
                delivery_mode=2,  # Make message persistent
            ))
        
        connection.close()
        return {'message': 'Producto agregado con éxito', 'producto_id': nuevo_producto.id}
    except Exception as e : 
        print(str(e))
        session.rollback()
        return None