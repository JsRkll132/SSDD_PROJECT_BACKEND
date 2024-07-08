from flask import Flask
from dotenv import load_dotenv
from .Routes.routes import users_routes
from flask_cors import CORS
load_dotenv()
import os
def create_app() : 
    app = Flask(__name__)
    CORS(app,origins="*")
    app.config['SQLALCHEMY_DATABASE_URI']= os.getenv('DATABASE_URL')
    print(os.getenv('DATABASE_URL'))
    app.register_blueprint(users_routes)
    return app


