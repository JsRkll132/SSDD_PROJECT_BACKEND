import json
import pika
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker

from app.Rabbitmq.rabbitmq import get_rabbitmq_connection
from ..Models.models import Carrito, ItemCarrito, Reserva, Usuario,Producto,Factura,Orden,ItemOrden,Rol
import os


engine = create_engine(os.getenv('DATABASE_URL'))
Session = sessionmaker(bind=engine)
session = Session()







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

def confirmar_ordenRepository(orden_id,metodo_pago) : 
    try :
        print(orden_id)
        if not orden_id or not metodo_pago:
            return {'status':0,'error': 'Falta el ID de la orden o el método de pago'}
        
        orden = session.query(Orden).filter_by(id=orden_id).first()
        if not orden:
            return {'status':0,'error': 'Orden no encontrada'}
        
        cliente = orden.cliente
        
        total_orden = sum(item.precio_compra * item.cantidad for item in orden.items)
        nueva_factura = Factura(orden_id=orden_id, monto=total_orden, pagada=True)
        session.add(nueva_factura)
        if metodo_pago == 'score_crediticio':
            if cliente.score_crediticio < total_orden:
                return {'status':0,'error': 'Score crediticio insuficiente'}
            cliente.score_crediticio -= total_orden
        elif metodo_pago == 'credito':
            if cliente.credito < total_orden:
                return {'status':0,'error': 'Crédito insuficiente'}
            cliente.credito -= total_orden
        else:
            return {'status':0,'error': 'Método de pago no válido'}
        
        orden.estado = 'Confirmada'
        session.commit()
        message = {
            'orden_id': orden_id,
            'metodo_pago': metodo_pago,
            'cliente_email': cliente.correo,
            'factura_monto': nueva_factura.monto,
            'factura_fecha': nueva_factura.fecha_emision.isoformat(),
        }
        publish_message('order_confirmations', message)
        return {'status':1,'message': 'Orden confirmada exitosamente'}
    except Exception as e :
        session.rollback()
        print(str(e))
        return {'status':-1,'error': 'Error en la operacion','info':str(e)}
    

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
""" 
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
    
"""  
    
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
    

def obtener_ordenesRepository():
    try : 
        ordenes = session.query(
            Orden.id,
            Orden.fecha_creacion,
            Usuario.nombre_usuario,
            Orden.estado,
            func.sum(ItemOrden.cantidad * ItemOrden.precio_compra).label('monto_total')
        ).join(Usuario).join(ItemOrden).group_by(Orden.id, Usuario.nombre_usuario).all()
        ordenes_json = [{
                'id': orden.id,
                'fecha_creacion': orden.fecha_creacion,
                'estado':orden.estado,
                'nombre_usuario': orden.nombre_usuario,
                'monto_total': float(orden.monto_total)
            } for orden in ordenes]
        return ordenes_json
       
    except Exception as e:
        session.rollback()
        return {'status': -1, 'error': 'Ocurrió un error al momento obtener las ordenes', 'details': str(e)}
    
def obtener_ordenesByIdRepository(orden_id):
    try:
        # Consultar la orden y sus detalles
        orden = session.query(Orden).filter_by(id=orden_id).first()
        if not orden:
            return {'status': -1, 'error': 'Orden no encontrada'}
        
        detalles = [{
                'producto_id': item.producto_id,
                'nombre_producto': item.producto.nombre,
                'cantidad': item.cantidad,
                'precio_compra': item.precio_compra
            } for item in orden.items]
      
        
        orden_json = {
            'id': orden.id,
            'fecha_creacion': orden.fecha_creacion,
            'cliente': orden.cliente.nombre_usuario,
            'estado': orden.estado,
            'detalles': detalles
        }
        return {'status': 1, 'orden': orden_json}
    except Exception as e:
        session.rollback()
        return {'status': -1, 'error': 'Ocurrió un error al momento obtener las ordenes', 'details': str(e)}
    


def update_productoRepository(producto_id,product_data) : 
    try : 
        producto = session.query(Producto).filter_by(id=producto_id).first()
        if not producto:
            return {'status':0,'error': 'Producto no encontrado'}
        if 'nombre' in product_data:
            producto.nombre = product_data['nombre']
        if 'precio' in product_data:
            producto.precio = product_data['precio']
        if 'sku' in product_data:
            producto.sku = product_data['sku']
        if 'stock' in product_data:
            producto.stock = product_data['stock']
        if 'url_imagen' in product_data:
            producto.url_imagen = product_data['url_imagen']
        session.commit()
        return {'status':1,'message': f'Producto {producto_id} actualizado exitosamente'}
    except Exception as e: 
        session.rollback()
        return  {'status':-1,'error': str(e)}


def delete_productoRepository(producto_id):
    try:
        producto = session.query(Producto).filter_by(id=producto_id).first()
        if not producto:
            return {'status': 0, 'error': 'Producto no encontrado'}
        
        session.delete(producto)
        session.commit()
        return {'status': 1, 'message': f'Producto {producto_id} eliminado exitosamente'}
    except Exception as e:
        session.rollback()
        return {'status': -1, 'error': str(e)}
    

def registerRepository(nombre_usuario, contrasena, correo, rol_nombre='Cliente'):
    try : 
        if session.query(Usuario).filter_by(nombre_usuario=nombre_usuario).first():
            return None, F"El usuario {nombre_usuario} ya existe"

        rol = session.query(Rol).filter_by(nombre=rol_nombre).first()
        if not rol:
            rol = Rol(nombre=rol_nombre)
            session.add(rol)
            session.commit()

        nuevo_usuario = Usuario(
            nombre_usuario=nombre_usuario,
            contrasena=contrasena,
            correo=correo,
            rol_id=rol.id
        )
        session.add(nuevo_usuario)
        session.commit()
        return nuevo_usuario, None
    except Exception as e :
        print(str(e))
        session.rollback()
        return {'status': -1, 'error': 'Ocurrio un error en la conexion', 'details': str(e)}
    

def obtener_usuario_por_nombre(nombre_usuario):
    try: 
        return session.query(Usuario).filter_by(nombre_usuario=nombre_usuario).first()
    except Exception as e :
        session.rollback()
        print(str(e))


def loginRepository(nombre_usuario, contrasena):
    try:
        usuario = session.query(Usuario).filter_by(nombre_usuario=nombre_usuario).first()
        
        if not usuario or usuario.contrasena != contrasena:
            return None, 'Nombre de usuario o contraseña incorrectos'
        
        return usuario, None
    
    except Exception as e:
        session.rollback()
        print(str(e))
        return None, 'Ocurrió un error en la conexión'        