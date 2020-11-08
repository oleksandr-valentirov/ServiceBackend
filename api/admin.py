from fastapi import APIRouter
from datetime import datetime
from typing import Optional

from auth import Security
from database import db, connect
from models import users_table, UserInDB, schedule_table, NewUser, get_user_time_slots


# ==================================================================================
# ======================== configuration ===========================================
router = APIRouter()


@router.on_event("startup")
@connect
async def startup():  # create an admin on first start
    check_admin = users_table.select(users_table.c.id).where(users_table.c.role_id == 2)
    admin = await db.fetch_one(check_admin)
    if not admin:
        admin = {
            'username': 'admin',
            'hashed_password': Security.crypt('admin'),
            'role_id': 2
        }
        query = users_table.insert().values([admin])
        await db.execute(query)

# ==================================================================================


@router.get('/list_clients')
async def list_clients():
    query = users_table.select().with_only_columns([users_table.c.id, users_table.c.full_name]).where(users_table.c.role_id == 0)
    return await db.fetch_all(query)


@router.get('/client/{client_id}')
async def get_clients_schedule(client_id: int, date: Optional[str] = ''):
    if date:
        date_obj = datetime.strptime(date, "%d-%m-%Y")
    else:
        date_obj = None

    query = get_user_time_slots(client_id, date_obj)
    return await db.fetch_all(query)


@router.post('/create_master')
async def create_master(user: NewUser):
    query = users_table.insert().values(username=user.username,
                                        hashed_password=Security.crypt(user.password),
                                        full_name=user.full_name,
                                        role_id=1
                                        )
    if not db.is_connected:
        await db.connect()
    last_record_id = await db.execute(query)
    res = {**user.dict(), "id": last_record_id}
    res.pop('password')
    return res
