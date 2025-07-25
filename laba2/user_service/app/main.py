from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext

from app import users_crud
from app.models import User, UserCreate, UserResponse, get_db

import json
from app.cache import redis_client

SECRET_KEY = "your-secret-key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

app = FastAPI()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        else:
            return username
    except JWTError:
        raise credentials_exception

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

@app.post("/token")
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    user = users_crud.get_user_by_login(db, form_data.username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not pwd_context.verify(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.login}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

# GET /users - Получить всех пользователей
@app.get("/users", response_model=List[UserResponse])
def read_users(skip: int = 0, limit: int = 100, 
               current_user: User = Depends(get_current_user), 
               db: Session = Depends(get_db)):
    users = db.query(User).offset(skip).limit(limit).all()
    return users

@app.get("/userscache", response_model=List[UserResponse])
def read_userscache(skip: int = 0, limit: int = 100, 
               current_user: User = Depends(get_current_user), 
               db: Session = Depends(get_db)):
    cached = redis_client.get("users:all")
    if cached:
            return json.loads(cached)

    users = db.query(User).all()
    print(users)
    serialized = [
        {
            "id": u.id,
            "login": u.login,
            "full_name": u.full_name,
            "email": u.email,
        }
        for u in users
    ]
    redis_client.set("users:all", json.dumps(serialized), ex=60)  # кэш на 60 секунд
    return serialized

# GET /users/{user_id} - Получить пользователя по ID
@app.get("/users/{user_id}", response_model=UserResponse)
def read_user(user_id: int,
              current_user: User = Depends(get_current_user), 
              db: Session = Depends(get_db)):
    db_user = users_crud.get_user(db, user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user

@app.get("/userscache/{user_id}", response_model=UserResponse)
def read_usercache(user_id: int,
              current_user: User = Depends(get_current_user),
              db: Session = Depends(get_db)):
    cache_key = f"user:{user_id}"
    if redis_client.exists(cache_key):
        cached_user = redis_client.get(cache_key)
        return json.loads(cached_user)
    
    db_user = users_crud.get_user(db, user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")

    user_dict = {
        "id": db_user.id,
        "login": db_user.login,
        "full_name": db_user.full_name,
        "email": db_user.email
    }

    redis_client.set(cache_key, json.dumps(user_dict), ex=180)
    return user_dict

@app.post("/register", response_model=UserResponse)
def register_user(user_data: UserCreate, db: Session = Depends(get_db)):
    print(user_data)
    existing_user = db.query(User).filter(User.login == user_data.login).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this login already exists"
        )

    hashed_password = pwd_context.hash(user_data.password)
    new_user = User(
        login=user_data.login,
        full_name=user_data.full_name,
        email=user_data.email,
        password_hash=hashed_password
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

# PUT /users/{user_id} - Обновить пользователя по ID
@app.put("/users/{user_id}", response_model=UserResponse)
def update_user(user_id: int, updated_data: UserCreate,
                current_user: User = Depends(get_current_user),
                db: Session = Depends(get_db)):
    db_user = users_crud.get_user(db, user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    # Обновляем данные (обратите внимание, что пароль здесь не обновляется — для этого можно добавить отдельную логику)
    db_user.login = updated_data.login
    db_user.full_name = updated_data.full_name
    db_user.email = updated_data.email
    db.commit()
    db.refresh(db_user)
    return db_user

# DELETE /users/{user_id} - Удалить пользователя по ID
@app.delete("/users/{user_id}", response_model=UserResponse)
def delete_user(user_id: int,
                current_user: User = Depends(get_current_user),
                db: Session = Depends(get_db)):
    db_user = users_crud.get_user(db, user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    db.delete(db_user)
    db.commit()
    return db_user

# Запуск сервера
# http://localhost:8000/openapi.json swagger
# http://localhost:8000/docs портал документации

# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(app, host="0.0.0.0", port=8000)