from sqlalchemy import Column, Integer, String, Boolean, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import os
# Declarative base
load_dotenv()
Base = declarative_base()

# Modelo para la tabla clientes
class Cliente(Base):
    __tablename__ = 'clientes'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    nombre_usuario = Column(String(50), unique=True, nullable=False)
    contrasena = Column(String(100), nullable=False)
    riesgo = Column(Boolean, nullable=False, default=False)
    correo = Column(String(100))

# URL de conexión a la base de datos


# Crear el motor de la base de datos
engine = create_engine(os.getenv('DATABASE_URL_EQUIFAX'))

# Crear todas las tablas
Base.metadata.create_all(engine)

# Crear una sesión para interactuar con la base de datos
Session = sessionmaker(bind=engine)
session = Session()
