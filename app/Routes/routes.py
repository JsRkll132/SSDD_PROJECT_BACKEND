import json
from flask import Blueprint, jsonify, request
import pika

from app.Rabbitmq.rabbitmq import get_rabbitmq_connection
from app.Repository.repository import AddToCarRepository, agregar_productoRepository, confirmar_ordenRepository, confirmar_pagoRepository, delete_item_from_cartRepository, delete_productoRepository, facturas_pendientesRepository, generar_orden, getRoles, listar_productos, loginRepository, obtener_ordenesByIdRepository, obtener_ordenesRepository, obtener_productos_en_carritosRepository, pagarRepository, registerRepository, update_productoRepository, verificar_scoreRepository
from app.utils import Security


users_routes = Blueprint('users_routes',__name__)
@users_routes.get('/main')
def init_app() : 
    return 'e_e'



@users_routes.get('/api/roles')
def getRolesRoute() : 
    try : 
        roles = getRoles()
        return jsonify(roles),200
    except : 
        return jsonify(None),500
    

@users_routes.route('/api/generar_orden', methods=['POST'])
def generar_orden_endpoint():
    try : 
        data = request.get_json()
        usuario_id = data.get('usuario_id')
        
        if not usuario_id:
            return jsonify({'status': -1, 'error': 'usuario_id es requerido'}), 400
        
        response = generar_orden(usuario_id)
        if response['status'] == -1:
            return jsonify(response), 400
        else:
            return jsonify(response), 201
    except Exception as e : 
        print(str(e))
        return jsonify({'error': 'Error en la operacion'}),500
        
@users_routes.route('/api/pagar', methods=['POST'])
def pagarRoute():
    try : 
        data = request.json
        orden_id = data['orden_id']
        metodo_pago = data['metodo_pago']
        response_req = pagarRepository(data,orden_id,metodo_pago)
        if response_req['error'] : 
            return jsonify(response_req),401
        if response_req!=None : 
            return jsonify(response_req),201
    except : 
        return jsonify({'error': 'Error en la operacion'}),500


@users_routes.route('/api/verificar_score', methods=['POST'])
def verificar_score():
    try :
        data = request.json
        cliente_id = data['cliente_id']
        response = verificar_scoreRepository(cliente_id)
        if response['error'] :
            return jsonify(response),404
        if response['status'] == 1:
            return jsonify(response),200
        if response['status'] == 0 :
            return jsonify(response),400
    except Exception as e :
        return jsonify({'error': 'Error en la operacion'}),500
    
@users_routes.route('/api/facturas_pendientes', methods=['GET'])
def facturas_pendientes():
    try : 
        response = facturas_pendientesRepository()
        if response!=None:
            return jsonify(response),200
        else : 
            return jsonify({'error': 'Error en la operacion'}),500
    except  Exception as e: 
        print(str(e))
        return jsonify({'error': 'Error en la operacion'}),500
    



@users_routes.route('/api/confirmar_pago', methods=['POST'])
def confirmar_pago():
    try :
        data = request.json
        factura_id = data['factura_id']
        response = confirmar_pagoRepository(factura_id)
        if response['error'] :
            return jsonify(response),404
        return jsonify(response),200
    except  Exception as e: 
        print(str(e))
        return jsonify({'error': 'Error en la operacion'}),500
    

@users_routes.route('/api/agregar_producto', methods=['POST'])
def agregar_producto():
    try :
        data = request.json
        response = agregar_productoRepository(data)
        if response!=None : 
            """connection = get_rabbitmq_connection()
            channel = connection.channel()
            channel.queue_declare(queue='ordenes', durable=True)
            
            message = json.dumps({'orden_id': data['producto_id']})
            channel.basic_publish(
                exchange='',
                routing_key='ordenes',
                body=message,
                properties=pika.BasicProperties(
                    delivery_mode=2,  # Make message persistent
                ))
            
            connection.close()"""
            
            return jsonify(response),201
    except  Exception as e: 
        print(str(e))
        return jsonify({'error': 'Error en la operacion'}),500
    
@users_routes.route('/api/listar_productos', methods=['GET'])
def listar_productosRoutes() : 
    try : 
        response = listar_productos()
        return jsonify(response),200
    except Exception as e : 
        print(str(e))
        return jsonify({'error': 'Error en la operacion'}),500        
"""
@users_routes.route('/api/login',methods=['POST'])
def login_userRoutes() : 
    try :
        user_data = request.json
        print(user_data)
        response = login_userRepository(user_data)
        
        if response['status']==-1 or response['status'] == 0  : 
            return jsonify(response) ,503
        elif response['status']==1 : 
            return jsonify(response) ,201
    
    except Exception as e :
        print(str(e))
        return jsonify({'error': 'Error en la operacion'}),500                
    """
@users_routes.route('/api/addtoCar', methods=['POST'])
def AddToCarRoutes():
    try:
        data = request.get_json()
        usuario_id = data.get('usuario_id')
        producto_id = data.get('producto_id')
        cantidad = data.get('cantidad')

        if not usuario_id or not producto_id or not cantidad:
            return jsonify({'status': -1, 'error': 'usuario_id, producto_id, y cantidad son necesarios'}), 400

        result = AddToCarRepository(usuario_id, producto_id, cantidad)

        if result['status'] == -1:
            return jsonify(result), 400
        return jsonify(result), 201
    except Exception as e:
        return jsonify({'status': -1, 'error': 'Ocurrió un error procesando la solicitud', 'details': str(e)}), 500          

@users_routes.route('/api/productos_en_carritos', methods=['GET'])
def obtener_productos_en_carritosRoutes():
    try:
        usuario_id = request.args.get('usuario_id')
        if not usuario_id:
            return jsonify({'status': 0, 'error': 'Falta el ID del usuario'}), 400

        data = obtener_productos_en_carritosRepository(int(usuario_id))
        return jsonify(data), 200

    except Exception as e:
        return jsonify({'status': -1, 'error': 'Ocurrió un error procesando la solicitud', 'details': str(e)}), 500           


@users_routes.route('/api/eliminaritem', methods=['POST'])
def delete_from_carritoRoutes():
    try:
        data = request.get_json()
        usuario_id = data.get('usuario_id')
        producto_id = data.get('producto_id')

        if not usuario_id or not producto_id:
            return jsonify({'status': -1, 'error': 'usuario_id y producto_id son necesarios'}), 400

        response = delete_item_from_cartRepository(usuario_id, producto_id)
        if response['status'] == -1:
            return jsonify(response), 400
        return jsonify(response), 200
    except Exception as e:
        return jsonify({'status': -1, 'error': 'Ocurrió un error procesando la solicitud', 'details': str(e)}), 500


@users_routes.route('/api/ordenes', methods=['GET'])
def obtener_ordenesRoutes():
    try:
        usuario_id = request.args.get('usuario_id')
        if not usuario_id:
            return jsonify({'status': 0, 'error': 'Falta el ID del usuario'}), 400

        data = obtener_ordenesRepository(usuario_id)
        if data['status'] == 1:
            return jsonify(data)
        else:
            return jsonify(data), 500

    except Exception as e:
        return jsonify({'status': -1, 'error': 'Ocurrió un error procesando la solicitud', 'details': str(e)}), 500

@users_routes.route('/api/ordenes/<int:orden_id>', methods=['GET'])
def obtener_ordenesByIdRoutes(orden_id) : 
    try : 
        data = obtener_ordenesByIdRepository(orden_id)
        if data['status']==1 : 
            return  jsonify(data),200
        else : 
            return jsonify(data),400
    except Exception as e:
        return jsonify({'status': -1, 'error': 'Ocurrió un error procesando la solicitud', 'details': str(e)}), 500


@users_routes.route('/api/confirmar_orden', methods=['POST'])
def confirmar_ordenRoutes():
    try:
        data = request.json
        orden_id = data.get('orden_id')
        metodo_pago = data.get('metodo_pago')  # 'score_crediticio' o 'credito'
        print(data)
        response =  confirmar_ordenRepository(orden_id,metodo_pago)
        print(response	)
        if response['status'] == 1 : 
            return response,201
        elif  response['status'] == 0 : 
            return response, 400
        else : 
            return response , 500
    except Exception as e:
        print(str(e))
        return jsonify({'status': -1, 'error': 'Ocurrió un error procesando la solicitud', 'details': str(e)}), 500
    

@users_routes.route('/api/productos/<int:producto_id>', methods=['PUT'])
def update_productoRoutes(producto_id):
    try : 
        product_data = request.json
        response = update_productoRepository(producto_id,product_data)
        if response['status'] == 1 : 
            return jsonify(response), 200
        if response['status'] == 0 : 
            return jsonify(response),400
        if response['status'] == -1 : 
            return jsonify(response),500
    except Exception as e : 
        print(str(e))
        return jsonify({'status': -1, 'error': 'Ocurrió un error procesando la solicitud', 'details': str(e)}), 500
    

@users_routes.route('/api/productos/<int:producto_id>', methods=['DELETE'])
def delete_productoRoutes(producto_id):
    try:
        response = delete_productoRepository(producto_id)
        if response['status'] == 1:
            return jsonify(response), 200
        if response['status'] == 0:
            return jsonify(response), 400
        if response['status'] == -1:
            return jsonify(response), 500
    except Exception as e:
        print(str(e))
        return jsonify({'status': -1, 'error': 'Ocurrió un error procesando la solicitud', 'details': str(e)}), 500


@users_routes.route('/api/register', methods=['POST'])
def registerRoutes():
    try : 
        data = request.get_json()
        nombre_usuario = data['nombre_usuario']
        contrasena = data['contrasena']
        correo = data['correo']
        rol_nombre = data.get('rol', 'Cliente')

        usuario, error = registerRepository(nombre_usuario, contrasena, correo, rol_nombre)
        if error:
            return jsonify({'status': 0,"message": error}), 400

        return jsonify({'status': 1,"message": "Usuario registrado exitosamente"}), 201
    except Exception as e : 
        print(str(e))
        return jsonify({'status': -1, 'error': 'Ocurrio un error en la conexion', 'details': str(e)}), 500
    


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



@users_routes.route('/api/login', methods=['POST'])
def loginRoutes():
    try:
        data = request.get_json()
        nombre_usuario = data['nombre_usuario']
        contrasena = data['contrasena']
        
        usuario, error = loginRepository(nombre_usuario, contrasena)
        if error:
            return jsonify({'status': 0, 'message': error}), 401
        
        # Aquí podrías generar un token JWT o similar si lo deseas
        token = Security.Security().generate_token(usuario)
        return jsonify({'status': 1, 'message': 'Inicio de sesión exitoso', 'data_info': {
            'id': usuario.id,
            'nombre_usuario': usuario.nombre_usuario,
            'correo': usuario.correo,
            'rol': usuario.rol.id
        },"token":token},), 200
    
    except Exception as e:
        print(str(e))
        return jsonify({'status': -1, 'error': 'Ocurrió un error en la conexión', 'details': str(e)}), 500


@users_routes.route('/api/cargar_credito', methods=['POST'])
def cargar_credito():
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        amount = data.get('amount')

        if not user_id or not amount:
            return jsonify({'status': -1, 'error': 'user_id y amount son necesarios'}), 400

        publish_message('credito_carga', data)
        return jsonify({'status': 1, 'message': 'Solicitud de recarga de crédito en proceso'}), 202

    except Exception as e:
        return jsonify({'status': -1, 'error': 'Ocurrió un error procesando la solicitud', 'details': str(e)}), 500
