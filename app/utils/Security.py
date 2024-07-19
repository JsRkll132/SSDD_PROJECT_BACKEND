import datetime
import jwt
from dotenv import load_dotenv
import pytz
import os
load_dotenv()
class Security() :
    tz = pytz.timezone('America/Lima')
    @classmethod
    def generate_token(cls,auth_user) :
        payload = {
            'iat' :datetime.datetime.now(tz=cls.tz),
            'exp' :datetime.datetime.now(tz=cls.tz)+datetime.timedelta(minutes=120) ,
            'data_info': {
            'id': auth_user.id,
            'nombre_usuario': auth_user.nombre_usuario,
            'correo':auth_user.correo,
            'rol': auth_user.rol.id
        }
             
        }
        print(payload)
        
        print(os.getenv('JWT_KEY'))
        
        key = jwt.encode(payload=payload,key=os.getenv('JWT_KEY'),algorithm = 'HS256')
        print (key)
        return jwt.encode(payload=payload,key=os.getenv('JWT_KEY'),algorithm = 'HS256')
        
    @classmethod
    def verify_token(cls,headers) : 
        if 'Authorization' in headers.keys() :
            authorization = headers['Authorization']
            encoded_token = authorization.split(" ")[1]