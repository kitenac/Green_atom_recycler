import random
import asyncio
from datetime import timedelta
from itertools import product       # to check avaliable combinations of composite PK   

from factory import LazyFunction
from factory.alchemy import SQLAlchemyModelFactory
from faker import Faker # for mocks data

from app.db import sessionFactory
from app.models import Models

from sqlalchemy import func
from sqlalchemy.future import select 
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas import *
from demon_main_IPC import send_command_to_demon 

# ==== helper functions for mocks - mb move `em in separate file later ====
def get_random_coord(digets: int = 6):
    '''get random float with given number of digets after comma '''
    random_float = random.uniform(0, 1)        # random float
    truncated = float(f"{random_float:.{digets}f}")   # truncating
    return random.randint(0,999999) + truncated

def time_m(x: int):
    '''time in minutes'''
    return timedelta(minutes=x)

# data predefined by task
WasteCategory = {
        'category': ['биоотходы', 'стекло', 'пластик'],
        'time_to_recycle': [time_m(x) for x in (1, 3, 4)] }


class ImpossibleToGenerateMock(Exception):
    '''Exception for situation when mock-generation isn`t posible due some constraints'''
    def __init__(self, message, solution):
        super().__init__(message)  
        self.solution = solution  # some compromise to bypass exception - advised from exception creator


async def get_sources_len() -> dict:
    ''' 
    tldr: index of last element for each of low-lvl - need for b in random.randint(a, b)
    
    get index of last element for each of low-lvl(without FK) tables, ex: 
    {
    'Polluter': 4,        # 0, 1, 2, 3, 4 | 5 in total, but 4 - last idx
    'Recycler': 1,        # 0, 1
    'WasteCategory': 2    # 0, 1, 2
    }    

    "sources" - bc these tables has keys acting as FK for other tables
    by index of last element we can generate random index for each source-table
    (to indicate entities by idx, not id)'''
    
    # regular COUNT(*) from tables
    async with sessionFactory() as session:
        polluter_count = await session.execute(
            select(func.count()).select_from(Models.Polluter_OO))
        recycler_count = await session.execute(
            select(func.count()).select_from(Models.Recycler_MNO))

    return  {
            'WasteCategory': 3-1,                 # always 2, bc by task there`s only 3 categories of wastes (2 = 3-1)
            'Polluter': polluter_count.scalar() - 1,        
            'Recycler': recycler_count.scalar() - 1       
        }




# ==== Tables without FK - "low-lvl" tables ====

faker = Faker() # faker object to generate truth-like data on different topics automatically

# Create Factory Classes:  This allows you to easily generate instances of your models with realistic data
# LazyFunction - helps create UNIQ valuse by delaing evaluation of code inside until initing an object | without it poles would get random value, but it`d be same for all instances - due it has been  already counted

class PolluterFactory(SQLAlchemyModelFactory):
    class Meta:
        model = Models.Polluter_OO
    name  = LazyFunction(lambda: f'OO {faker.company()}')
    x_geo = LazyFunction(get_random_coord)
    y_geo = LazyFunction(get_random_coord)


class RecyclerFactory(SQLAlchemyModelFactory):
    class Meta:
        model = Models.Recycler_MNO
    name  = LazyFunction(lambda: f'MNO {faker.company()}')
    x_geo = LazyFunction(get_random_coord)
    y_geo = LazyFunction(get_random_coord)


def WasteCategoryPseudoFactory():
    '''
    all possible wastecategories
     - pseudo - due data here isn`t random - predefined by task
    '''
    return [
        Models.WasteCategory(
                category=WasteCategory['category'][i], 
                time_to_recycle=WasteCategory['time_to_recycle'][i]) 
        for i in range(3)
    ]

# ===== Tables with FK ====

async def PolluterWasteFactory(size=1):
    '''
    Generate random Waste by random Polluter
        size - how many wastes to create
    '''
    async with sessionFactory() as session:    
        Sources = await get_sources_len()
        polluter_wastes = []
        
        # get polluters and waste_categories, to get their PK (FK in this table)
        polluters = await session.execute(select(Models.Polluter_OO))
        waste_categories = await session.execute(select(Models.WasteCategory))
        # retrive result-rows from awaited coroutines
        polluters, waste_categories = polluters.scalars().all(), waste_categories.scalars().all()

        # Actual Factory: producing size-count random entities
        for _ in range(size):
            amount = random.randint(1,5)
            # FKs - using relations through indexes, bc ids are auto-generated and not known yet - will be substituted by idx
            polluter_idx = random.randint(0, Sources['Polluter'])
            category_idx = random.randint(0, Sources['WasteCategory'] )

            waste = Models.PolluterWaste(
                amount      = amount,
                polluter_id = polluters[polluter_idx].id,
                category    = waste_categories[category_idx].category
            )
            polluter_wastes.append(waste)

        return polluter_wastes 



# much alike like coroutine above - just few differences in used vars
async def RecyclerStorageFactory(size=1):
    '''
    Generate random RecyclerStorages for random Recyclers with:
        random waste_category 
        random capacity

    '''
    async with sessionFactory() as session:    
        new_recycle_storages = []
        
        # get rcyclers and waste_categories, to get their PK (FK in this table)
        recyclers         = await session.execute(select(Models.Recycler_MNO))
        waste_categories  = await session.execute(select(Models.WasteCategory))
        recycler_storages = await session.execute(select(Models.RecyclerStorage))
        # retrive result-rows from awaited coroutines above
        recyclers, waste_categories, recycler_storages = recyclers.scalars().all(), waste_categories.scalars().all(), recycler_storages.scalars().all()

        # get PK of existing recycler storages to avoid aconflict PK in generation below 
        recycler_ids, waste_categories = {x.id for x in recyclers}, {x.category for x in waste_categories}
        all_possible_PK = set(product(recycler_ids, waste_categories))
        recycler_PKs    = {(x.recycler_id, x.category) for x in recycler_storages}
        PK_pool = all_possible_PK.difference(recycler_PKs) # pool of possible PK pairs 

        if len(PK_pool) < size:
            '''PK constraint met, advicing solution to use size=len(PK_pool) next time'''
            raise ImpossibleToGenerateMock(solution=len(PK_pool), message=f"The size of PK_pool = {len(PK_pool)} < required size = {size}\n change size to {len(PK_pool)}")
        
        PK_pool = random.sample(sorted(PK_pool), k=size) # try to take size-count uniq PK from pool of avaliable PK | sorted(PK_pool) - it`s requirment for sets to fit in random.sample

        # Actual Factory: producing size-count random entities
        for i in range(size):
            capacity = random.randint(1,5)
            # FKs - using relations through indexes, bc ids are auto-generated and not known yet - will be substituted by idx
            recycler_id, category = PK_pool[i] 

            waste = Models.RecyclerStorage(
                capacity    = capacity,
                recycler_id = recycler_id,
                category    = category
            )
            new_recycle_storages.append(waste)

        return new_recycle_storages




'''
RecyclerWaste 
- #TODO will be populated by backend itself (requires logic)


'''

class MockAtomEco:
    '''
    Mocks for atom eco app
    
        1. Create DB session 
        2. Generate ORM-objects filled with auto-generated data (by Faker) 
        3. Pull objects to DB
    '''
    @staticmethod
    async def initial_populate():
        '''
         add random records to low-lvl tables (without FK)
        '''
        async with sessionFactory() as session:  # Create a new session
            # Generate entities instances - using the factory | generate_ - in-memory creation - no need to db-session passing
            polluter = PolluterFactory.generate_batch(strategy='build', size=5) 
            recycler = RecyclerFactory.generate_batch(strategy='build', size=2)
            waste_category = WasteCategoryPseudoFactory()

            # merge all new entities in one array to add them all in db 
            new_entities = [
                *polluter, 
                *recycler, 
                *waste_category
            ] 
            # pull entities to the DB
            for el in new_entities:
                print(el.__dict__) # TODO: move in logs
                session.add(el) 
                await session.commit() 
    


    @staticmethod
    async def OO_MNO_wastes_populate():
        '''
        Populate High-lvl tables (with FK)

        Generate -random: 
          - Waste by random Polluter 
          - Storages of random sizes for Recyclers
        '''
        async with sessionFactory() as session:  # Create a new session
            # Generate entities instances - using the factory | generate_ - in-memory creation - no need to db-session passing
            polluter_waste = await PolluterWasteFactory(size=5)
            
            # handle possible PK not enough case and folow solution
            try:
                recycler_storage = await RecyclerStorageFactory(size=5)
            except ImpossibleToGenerateMock as e:
                if e.solution > 0:
                    recycler_storage = await RecyclerStorageFactory(size=e.solution) 
                else:
                    print('all possible RecyclersStorages already created')

            # merge all new entities in one array to add them all in db 
            new_entities = [
                *polluter_waste,
                *recycler_storage
            ] 
            # pull entities to the DB
            for el in new_entities:
                print(el.__dict__) # TODO: move in logs
                session.add(el) 
                await session.commit() 



    # ======= For API rutes: backend IPC with Demon =======
    # to be used from app`s routes, not from this file !!! (requires Demon to be started)
    @staticmethod
    async def MOCK_OO_wastes_populate():
            '''
            Populate polluter_wastes

            Generate -random: 
            - Waste by random Polluter 
            '''
            async with sessionFactory() as session:  # Create a new session
                # Generate entities instances - using the factory | generate_ - in-memory creation - no need to db-session passing
                polluter_waste = await PolluterWasteFactory(size=5)            
                # pull entities to the DB
                for el in polluter_waste:
                    print(el.__dict__) # TODO: move in logs
                    session.add(el) 
                    await session.commit() 
                    # feed data to Demon via IPC
                    send_command_to_demon('PolluterWaste_ADD', convert_to_pydentic(el, PolluterWaste))

    @staticmethod
    async def MOCK_MNO_wastes_populate():
        '''
        Populate High-lvl tables (with FK)

        Generate -random: 
          - Storages of random sizes for Recyclers
        '''
        async with sessionFactory() as session:  # Create a new session            
            # handle possible PK not enough case and folow solution
            try:
                recycler_storage = await RecyclerStorageFactory(size=5)
            except ImpossibleToGenerateMock as e:
                if e.solution > 0:
                    recycler_storage = await RecyclerStorageFactory(size=e.solution) 
                else:
                    print('all possible RecyclersStorages already created')
                    return 'all possible RecyclersStorages already created'

            # pull entities to the DB
            for el in recycler_storage:
                print(el.__dict__) # TODO: move in logs
                session.add(el) 
                await session.commit() 
                # feed data to Demon via IPC
                send_command_to_demon('RecyclerStorage_ADD', convert_to_pydentic(el, RecyclerStorage))


if __name__ == "__main__":
    # fill low-lvl tables (without FK) - at start
    asyncio.run(MockAtomEco.initial_populate())

    # fill high-lvl tables (with FK)
    asyncio.run(MockAtomEco.OO_MNO_wastes_populate())

    # fill buiesness logic related table - RecyclerWastes
    # TODO - some API method call to handle wastes
    # AFTERNOTE - actually there`s demon that manages this table row`s life-cycle - when to create new RecyclerWaste and when to release it

# =========================================================== 
# а ещё моки можно в теcтах использовать: - мб пригодится
# пример ниже
'''
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from your_model_file import Base, User, Post  # Adjust the import as necessary

# Set up the database for testing
DATABASE_URL = "sqlite:///:memory:"  # Use an in-memory SQLite database for testing
engine = create_engine(DATABASE_URL)
Base.metadata.create_all(bind=engine)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def test_user_creation():
    session = SessionLocal()
    user = UserFactory.create()  # Create a user instance
    assert user.id is not None  # Check that the user has been created
    session.add(user)
    session.commit()
    session.close()

def test_post_creation():
    session = SessionLocal()
    post = PostFactory.create()  # Create a post instance
    assert post.id is not None  # Check that the post has been created
    assert post.owner is not None  # Ensure the post has an owner
    session.add(post)
    session.commit()
    session.close()
'''