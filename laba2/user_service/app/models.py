import time
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, TIMESTAMP
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@db:5432/userdb")
engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    login = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(128), nullable=False)
    full_name = Column(String(100))
    email = Column(String(100))
    created_at = Column(TIMESTAMP)

# Модель Pydantic для валидации данных
class UserCreate(BaseModel):
    login: str
    full_name: str
    email: str
    password: str
    # id: int

class UserResponse(BaseModel):
    id: int
    full_name: str

    class Config:
        orm_mode = True

try:
    Base.metadata.create_all(bind=engine)
except:
    time.sleep(5)
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()    