import json
import pika
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.Rabbitmq.rabbitmq import get_rabbitmq_connection
from ..Models.models import Carrito, ItemCarrito, Reserva, Usuario,Producto,Factura,Orden,ItemOrden,Rol
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


def deleteFromCarritoRepository(item_id) : 
    try :
        session.query(ItemCarrito).filter_by(id=item_id).delete()
        session.commit()
        return {'status': 1, 'message': 'Producto eliminado del carrito', 'item_carrito_deleted': item_id}
    except Exception as e : 
        session.rollback()
        return {'status': -1, 'error': 'Ocurrió un error al momento de quitar el item', 'details': str(e)}
def generar_orden(usuario_id):
    try:
        # Obtener el carrito del usuario
        carrito = session.query(Carrito).filter_by(usuario_id=usuario_id).first()
        if not carrito or not carrito.items:
            return {'status': -1, 'error': 'No hay ítems en el carrito para generar la orden'}

        # Crear una nueva orden
        nueva_orden = Orden(cliente_id=usuario_id, estado='Pendiente')
        session.add(nueva_orden)
        session.flush()  # Para obtener el id de la orden antes de commit

        # Detallar los productos comprados y actualizar stock
        for item_carrito in carrito.items:
            producto = item_carrito.producto

            # Verificar si la cantidad solicitada supera el stock disponible
            if item_carrito.cantidad > producto.stock:
                return {'status': -1, 'error': f'Cantidad solicitada del producto {producto.nombre} supera el stock disponible'}

            # Actualizar el stock del producto
            producto.stock -= item_carrito.cantidad

            # Crear un nuevo ítem de orden
            item_orden = ItemOrden(
                orden_id=nueva_orden.id,
                producto_id=item_carrito.producto_id,
                cantidad=item_carrito.cantidad,
                precio_compra=producto.precio,
                
            )
            session.add(item_orden)

        # Borrar los ítems del carrito
        session.query(ItemCarrito).filter_by(carrito_id=carrito.id).delete()

        # Guardar cambios en la base de datos
        session.commit()

        return {'status': 0, 'message': 'Orden generada correctamente', 'orden_id': nueva_orden.id}

    except Exception as e:
        session.rollback()
        return {'status': -1, 'error': 'Ocurrió un error al momento de generar la orden', 'details': str(e)}

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
    
def login_userRepository(user_data) :
    try : 
        user = session.query(Usuario).filter_by(nombre_usuario=user_data['username']).first()
  
        if   user == None  : 
            return {'status':0,'error' : 'Usuario no existe'}
        elif user.contrasena != user_data['password'] : 
            return {'status':0,'error' : 'Contraseña mal puesta'}
        else:
            return {'status':1,'data_info':{'usuario' :user.nombre_usuario ,'id':user.id,'rol':user.rol_id}}

    except Exception as e : 
        print(str(e))
        session.rollback()
        return {'status':-1,'error' : 'Ocurrio un error al iniciar sesion.'}
    

    
def AddToCarRepository(carrito_id, producto_id, cantidad):
    try:
        # Obtener el producto para verificar el stock
        producto = session.query(Producto).filter_by(id=producto_id).first()
        
        if not producto:
            return {'status': -1, 'error': 'Producto no encontrado'}
        
        # Verificar si el producto ya está en el carrito
        item_carrito = session.query(ItemCarrito).filter_by(carrito_id=carrito_id, producto_id=producto_id).first()
        
        if item_carrito:
            # Si el producto ya está en el carrito, calcular la nueva cantidad
            nueva_cantidad = cantidad
        else:
            # Si el producto no está en el carrito, la nueva cantidad es simplemente la cantidad proporcionada
            nueva_cantidad = cantidad
        
        # Verificar si la nueva cantidad supera el stock disponible
        if nueva_cantidad > producto.stock:
            return {'status': -1, 'error': 'Cantidad solicitada supera el stock disponible'}
        
        if item_carrito:
            # Actualizar la cantidad del producto en el carrito
            item_carrito.cantidad = nueva_cantidad
        else:
            # Agregar un nuevo item al carrito
            nuevo_item = ItemCarrito(carrito_id=carrito_id, producto_id=producto_id, cantidad=cantidad)
            session.add(nuevo_item)
        
        # Guardar cambios en la base de datos
        session.commit()
        return {'status': 1, 'message': f'Producto {producto.id} añadido/actualizado correctamente en el carrito'}
    
    except Exception as e:
        # En caso de error, revertir la transacción
        session.rollback()
        return {'status': -1, 'error': 'Ocurrió un error al momento de añadir al carrito', 'details': str(e)}


def obtener_productos_en_carritosRepository():
    try:
        # Consulta para obtener el nombre del producto, ID del producto y otros atributos junto con la cantidad en el carrito, ID del carrito y ID del item de carrito
        query = session.query(
                    Producto.nombre.label('nombre_producto'),
                    Producto.id.label('id_producto'),
                    Producto.precio,
                    Producto.sku,
                    Producto.stock,
                    ItemCarrito.cantidad.label('cantidad_en_carrito'),
                    ItemCarrito.carrito_id,
                    ItemCarrito.id.label('item_carrito_id')
                ).join(
                    ItemCarrito,
                    Producto.id == ItemCarrito.producto_id,
                   
                )
        
        # Ejecutar la consulta y obtener los resultados
        resultados = query.all()

        # Convertir resultados a formato JSON
        productos_en_carritos_json = []
        for resultado in resultados:
            producto_json = {
                'nombre_producto': resultado.nombre_producto,
                'id_producto': resultado.id_producto,
                'precio': float(resultado.precio),
                'sku': resultado.sku,
                'stock': resultado.stock,
                'cantidad_en_carrito': resultado.cantidad_en_carrito,
                'carrito_id': resultado.carrito_id,
                'item_carrito_id': resultado.item_carrito_id
            }
            productos_en_carritos_json.append(producto_json)

        return productos_en_carritos_json

    except Exception as e:
        session.rollback()
        return {'status': -1, 'error': 'Ocurrió un error al momento obtener los carritos', 'details': str(e)}