import hashlib
from datetime import datetime
from random import randbytes
from uuid import UUID

from fastapi import FastAPI, status, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from rabbit_mq.publisher import publish_email_data
from verify_token import get_current_user

from database_config import get_db
from schemas import UserSchema, UserCreateSchema
from hash import hash_password

import models

app = FastAPI(title='users')

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)


@app.get("/")
async def ping():
    return {"message": "Hello World. This is users microservice"}


@app.get("/auth_ping")
async def auth_ping(current_user=Depends(get_current_user)):
    return {"message": "Hello. You have successfully authenticated."}


@app.get("/users", status_code=status.HTTP_200_OK, response_model=list[UserSchema])
async def get_users_list(session: AsyncSession = Depends(get_db)):
    users_list = await session.execute(
        select(models.User))
    return users_list.scalars().all()


@app.get("/users/{user_id}", status_code=status.HTTP_200_OK, response_model=UserSchema)
async def get_user(user_id: UUID, session: AsyncSession = Depends(get_db)):
    user = await session.get(models.User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@app.get("/users/username/{username}", status_code=status.HTTP_200_OK)
async def get_user_by_username(username: str, session: AsyncSession = Depends(get_db)):
    query = select(models.User).where(models.User.username == username)
    result = await session.execute(query)
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return user


@app.post("/users", status_code=status.HTTP_201_CREATED)
async def create_user(user_data: UserCreateSchema, session: AsyncSession = Depends(get_db)):
    user_data.password = await hash_password(user_data.password)
    new_user = models.User(**user_data.dict())

    token = randbytes(5)
    hashed_code = hashlib.sha256()
    hashed_code.update(token)
    verification_code = hashed_code.hexdigest()
    new_user.verification_token = verification_code
    session.add(new_user)
    await session.commit()
    await session.refresh(new_user)

    await publish_email_data(f"{new_user.username}:{new_user.email}:{new_user.verification_token}")
    return new_user


@app.put("/users/{user_id}", status_code=status.HTTP_200_OK)
async def update_user(user_id: UUID, user_data: UserCreateSchema, session: AsyncSession = Depends(get_db)):
    user = await session.get(models.User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    user_data.password = await hash_password(user_data.password)
    user_data_dict = user_data.dict(exclude_unset=True)
    for field, value in user_data_dict.items():
        setattr(user, field, value)

    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


@app.delete("/users/{user_id}", status_code=status.HTTP_200_OK)
async def delete_user(user_id: UUID, session: AsyncSession = Depends(get_db)):
    user = await session.get(models.User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    await session.delete(user)
    await session.commit()
    return "deleted"


@app.put('/verify-email')
async def verify_me(data: dict, current_user=Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    user_id = current_user.get('user_id')
    user = await session.get(models.User, user_id)

    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if user.verification_token == data.get('verification_token'):
        user.verification_token = None
        user.email_confirmed = True
        user.email_confirmed_date_time = datetime.utcnow()
        await session.commit()
        await session.refresh(user)
        return {"message": "Почта успешно подтверждена"}
    return {"message": "Нет доступа"}
