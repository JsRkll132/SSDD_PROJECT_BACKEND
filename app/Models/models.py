from flask_sqlalchemy import SQLAlchemy #
from sqlalchemy.sql import func
from enum import Enum as PyEnum
import os
from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, and_, create_engine, text
from sqlalchemy.orm import declarative_base,  sessionmaker,relationship
from sqlalchemy import func

Base = declarative_base()

class RoleEnum(PyEnum):
    CLIENTE = "Cliente"
    EMPLEADO_VENTAS = "Empleado de Ventas"
    EMPLEADO_COBRANZAS = "Empleado de Cobranzas"
    EMPLEADO_ALMACEN = "Empleado de Almascén"

class Rol(Base):
    __tablename__ = 'roles'
    id = Column(Integer, primary_key=True)
    nombre = Column(String(50), nullable=False)

class Usuario(Base):
    __tablename__ = 'usuarios'
    id = Column(Integer, primary_key=True)
    nombre_usuario = Column(String(50), unique=True, nullable=False)
    contrasena = Column(String(100), nullable=False)
    rol_id = Column(Integer, ForeignKey('roles.id'), nullable=False)
    score_crediticio = Column(Integer)
    credito = Column(Float, default=0.0)  # Nueva columna
    correo = Column(String(100))  
    rol = relationship('Rol')
    ordenes = relationship('Orden', back_populates='cliente')

class Producto(Base):
    __tablename__ = 'productos'
    id = Column(Integer, primary_key=True)
    nombre = Column(String(100), nullable=False)
    precio = Column(Float, nullable=False)
    sku = Column(String(50), unique=True, nullable=False)
    stock = Column(Integer, nullable=False)
    url_imagen = Column(String(255))

class Orden(Base):
    __tablename__ = 'ordenes'
    id = Column(Integer, primary_key=True)
    cliente_id = Column(Integer,ForeignKey('usuarios.id'), nullable=False)
    estado = Column(String(50), nullable=False)
    fecha_creacion = Column(DateTime(timezone=True), server_default=func.now())
    cliente = relationship('Usuario', back_populates='ordenes')
    items = relationship('ItemOrden', back_populates='orden')

class ItemOrden(Base):
    __tablename__ = 'items_orden'
    id = Column(Integer, primary_key=True)
    orden_id = Column(Integer, ForeignKey('ordenes.id'), nullable=False)
    producto_id = Column(Integer, ForeignKey('productos.id'), nullable=False)
    cantidad = Column(Integer, nullable=False)
    precio_compra = Column(Float, nullable=False)
    orden = relationship('Orden', back_populates='items')
    producto = relationship('Producto')

class Factura(Base):
    __tablename__ = 'facturas'
    id = Column(Integer, primary_key=True)
    orden_id = Column(Integer, ForeignKey('ordenes.id'), nullable=False)
    monto = Column(Float, nullable=False)
    fecha_emision = Column(DateTime(timezone=True), server_default=func.now())
    pagada = Column(Boolean, default=False)
    orden = relationship('Orden')

class Reserva(Base):
    __tablename__ = 'reservas'
    id = Column(Integer, primary_key=True)
    orden_id = Column(Integer, ForeignKey('ordenes.id'), nullable=False)
    fecha_reserva = Column(DateTime(timezone=True), server_default=func.now())
    orden = relationship('Orden')

Usuario.ordenes = relationship('Orden', order_by=Orden.id, back_populates='cliente')


class Carrito(Base):
    __tablename__ = 'carritos'
    
    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey('usuarios.id'), nullable=False)
    fecha_creacion = Column(DateTime, default=func.now())

    items = relationship("ItemCarrito", back_populates="carrito")

class ItemCarrito(Base):
    __tablename__ = 'items_carrito'
    
    id = Column(Integer, primary_key=True, index=True)
    carrito_id = Column(Integer, ForeignKey('carritos.id'), nullable=False)
    producto_id = Column(Integer, ForeignKey('productos.id'), nullable=False)
    cantidad = Column(Integer, nullable=False)

    carrito = relationship("Carrito", back_populates="items")
    producto = relationship("Producto")

engine = create_engine(os.getenv('DATABASE_URL'))

# Crear todas las tablas
Base.metadata.create_all(engine)

# Crear una sesión para interactuar con la base de datos
Session = sessionmaker(bind=engine)
session = Session()
