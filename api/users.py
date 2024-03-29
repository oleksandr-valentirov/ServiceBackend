from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta

from auth import Security

from database.models import UserInfo, UserInDB, SecuredUserInfo, Login, Token, NewUser, NewUserResponse
from database.schemas import roles_table
from database.database import db, connect
from database.crud import User


# ==================================================================================
# ======================== configuration ===========================================
router = APIRouter()


@router.on_event("startup")
@connect
async def startup():
    roles = await db.fetch_all(roles_table.select())
    if not roles:
        query = roles_table.insert().values([{'id': 0, 'role': 'client'},
                                             {'id': 1, 'role': 'master'},
                                             {'id': 2, 'role': 'admin'}]
                                            )
        await db.execute(query)


# ==================================================================================


@router.post('/create_user', response_model=NewUserResponse)
async def create_user(user: NewUser):
    query = User.create_user(username=user.username,
                             hashed_password=Security.crypt(user.password),
                             car_model=user.car_model,
                             full_name=user.full_name,
                             role_id=0
                             )
    if not db.is_connected:
        await db.connect()
    last_record_id = await db.execute(query)
    res = {**user.dict(), "id": last_record_id}
    res.pop('password')
    return res


@router.patch('/update_user_info', response_model=SecuredUserInfo)
async def update_user_info(info: UserInfo, user: UserInDB = Depends(Security.get_user_by_token)):
    """user can provide fields username, full_name, password and car_model to update them"""
    if not info:
        return
    elif not db.is_connected:
        await db.connect()

    fields_to_update = {}
    if info.username and info.username != user.username:
        check_name = User.check_name(info.username)
        res = await db.fetch_one(check_name)
        if not res:
            fields_to_update['username'] = info.username
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="username already exists",
                headers={"WWW-Authenticate": "Bearer"}
            )
    if info.password and not Security.verify_password(info.password, user.hashed_password):
        pop_pass = True
        fields_to_update['hashed_password'] = Security.crypt(info.password)
    else:
        pop_pass = False
    if info.full_name and info.full_name != user.full_name:
        fields_to_update['full_name'] = info.full_name
    if info.car_model and info.car_model != user.car_model:
        fields_to_update['car_model'] = info.car_model

    if fields_to_update:
        query = User.update_user_info(username=user.username, **fields_to_update)
        await db.execute(query)
        if pop_pass:
            fields_to_update.pop('hashed_password')
    return fields_to_update


@router.get('/me', response_model=SecuredUserInfo)
async def get_current_user(user: UserInDB = Depends(Security.get_user_by_token)):
    user = user.dict()
    user.pop('hashed_password')
    return dict(user)


@router.post('/login', response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = await Security.authenticate_user(Login(username=form_data.username, password=form_data.password))
    access_token_expires = timedelta(minutes=Security.ACCESS_TOKEN_EXPIRE_MINUTES)
    token = Security.create_access_token(data={"sub": user['username']}, expires_delta=access_token_expires)
    return {"access_token": token, "token_type": "bearer"}
