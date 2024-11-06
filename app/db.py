'''
Configuring access to Database
- engine (creds + database type)
- individual db-session for each request
'''
import asyncio
from sqlalchemy import text # for raw queries
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.models import Base # all Tables from models inherits from it => can create `em here 

from sqlalchemy import create_engine # just for creating DB - sync way is also afordable
from sqlalchemy_utils import database_exists, create_database

# dev/prod hosts ips
hosts = {
    'dev': '127.0.0.1',           # for development
    'prod': 'Postgres_Pet_PROD'   # when backend run as container | note: Docker`s internal DNS would resolve container`s ip by name of container
}
WORK_MODE = 'dev'  

host, port = hosts[WORK_MODE], '5432'
sql_vers, driver = 'postgresql', 'psycopg'  # info about db-engine psycopg: https://pypi.org/project/psycopg/ 
usr, pwd = 'root', 'root'                   # usr/pwd can be set via ENV vars (POSTGRES_USER, POSTGRES_PASSWORD) when db-image is creating
db_name = 'Atom_eco'



# creates database Atom_eco if not excists
engine = create_engine(f"postgresql://{usr}:{pwd}@{host}:{port}/{db_name}")
if not database_exists(engine.url):
    create_database(engine.url)


# creating async-engine for specific DB: https://docs.sqlalchemy.org/en/20/core/engines.html
DATABSE_URL = f"{sql_vers}+{driver}://{usr}:{pwd}@{host}:{port}/{db_name}"
engine = create_async_engine(DATABSE_URL)


# Создаём все таблицы, если ещё не были созданы
#Base.metadata.create_all(engine)
async def init_models():
    async with engine.begin() as conn:
        #await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

asyncio.run(init_models())




# object to create new sessions
sessionFactory = async_sessionmaker(bind=engine, expire_on_commit=False) 

async def get_db_session():
    '''
        access to db,
        auto-handle db session - close when session is unused (yield gives generator - which is single-use and`ll closed after use) 
    '''
    async with sessionFactory() as db:
        yield db  # yield - not return for Session - generator => session will be lost after using
