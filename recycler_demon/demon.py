'''
This demon:
- observes:        
    polls PolluterWaste table - queury of wastes from polluters
- manages wastes:  
    redistributes wastes between tables, 
    !!! the demon is THE ONLY part which populates RecyclerWastes - it`s the main purpose of this code-unit
- releases:        
    clears wastes from queuries: RecyclerWaste table (queury of wastes waiting for expirement) and PolluterWaste table

Demon runs as separate proces - by multiprocessing
# TODO: mb sepatate it to own microservice
'''
from math import pow
import asyncio
import datetime
import multiprocessing


from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas import * 
from app.db import sessionFactory
from app.models import Models



class RecyclerDemon:
    '''
    tldr: 
        demon manages RecyclerWastes table row`s life-cycle - when to create new RecyclerWaste and when to release it
        !!! inject _ADD methods on every ADD or UPDATE route in app to keep demon`s CACHE up to date 
        
    This demon:
    - observes:        
        polls PolluterWaste table - queury of wastes from polluters
    - manages wastes:  
        redistributes wastes between tables, 
        !!! the demon is THE ONLY part which populates RecyclerWastes - it`s the main purpose of this code-unit
    - releases:        
        clears wastes from queuries: RecyclerWaste table (queury of wastes waiting for expirement) and PolluterWaste table

    it runs as separate proces - by multiprocessing
    # TODO: mb sepatate it to own microservice    
    
    Purose: 
    - process handles wastemanagement parallelly
    - but there`s external life-cycle management - see Usage
     
    Usage:
    Demon loads DB tables in memory when started (there`s attribute for each table) 
    - then while app is working - it feeds Demon updated pieces of data - by _ADD methods to update tables if some of CUD operations happens


    Example usage:
    # main.py:
        from app.setup_app import start_app
        from recycler_demon.demon import RecyclerDemon
        
        # start the Demon to handle wastes
        My_RecyclerDemon = RecyclerDemon() # demon process to handle wastes
        My_RecyclerDemon.start()

        if __name__ == "__main__":
        try:
            start_app()
        finally:
            # if the app was broken - terminate demon process - not to allow zombies 
            My_RecyclerDemon.demon_process.terminate()

    # some_route.py
        from main import My_RecyclerDemon       # use created object of demon in our methods 

        async def create_pollutor():
            # some logic to add new polluter to DB
            polluter = Models.Polluter_OO(name=name, x_geo=x_geo, y_geo=y_geo)
            SessionLocal.add(polluter)
            await SessionLocal.commit()
            
            # feed the demon new data  in pydentic-DTO - due it can live without session
            send_command_to_demon('Polluter_OO_ADD', convert_to_pydentic(polluter, Polluter_OO))
                
    '''

    def asyncio_main_loop_runner(self):
        '''
        callback function that returns call to asyncio to start main loop with demon
            ps there`s no "async" near "def" due asyncio.run has syncronious context
        '''
        asyncio.run(self.main_loop())

    def __init__(self, IPC_queue: multiprocessing.Queue):
        # IPC-queue - queue of commands to manipulate Demon`s object attributes (from _ADD methods) from parent process - in main.py
        self.IPC_queue = IPC_queue

        # in-memory resources - read once from db and requires updating from app`s method
        # TODO move them to Redis 
        self.storage_slots:    list[RecyclerStorage]  # storage slots of all recyclers (from RecyclerStorage)
        self.wastes_queury:    list[PolluterWaste]    # queury from PolluterWaste wastes waiting to be moved into recycling_queury
        self.recycling_queury: list[RecyclerWaste]    # place where wastes placed to recycler waits to be released
        self.recyclers:        list[Recycler_MNO]   
        self.polluters:        list[Polluter_OO]    
        self.waste_categories: list[WasteCategory]  

        # [CACHE] little optimization - store distances in dict - like Cache - not to recount them each time
        # i.e. reuse already counted distances => sometimes distance counting will be O(1)
        self.distances = dict() # key = (polluter_id, recycler_id), value = distance**2

        # life-cycle management
        # - demon`s process avaliable as atribute => can be shutted down/started anywhere in RecyclerDemon object 
        self.demon_process  = multiprocessing.Process(target=self.asyncio_main_loop_runner)
        

    async def copy_DB(self):
        '''Copy DB entities to RAM''' # TODO Redis
        async with sessionFactory() as read_session:
            storage_slots    = await read_session.execute(select(Models.RecyclerStorage)) 
            wastes_queury    = await read_session.execute(select(Models.PolluterWaste))
            recycling_queury = await read_session.execute(select(Models.RecyclerWaste))
            polluters        = await read_session.execute(select(Models.Polluter_OO))
            recyclers        = await read_session.execute(select(Models.Recycler_MNO))
            waste_categories = await read_session.execute(select(Models.WasteCategory))

            # !!! store in DTO-pydentic, due sqlalchemy models are bound to session and`ll lost after session`s termination 
            self.storage_slots    = [RecyclerStorage(**el.__dict__) for el in storage_slots.scalars().all()] 
            self.wastes_queury    = [PolluterWaste  (**el.__dict__) for el in wastes_queury.scalars().all()]
            self.recycling_queury = [RecyclerWaste  (**el.__dict__) for el in recycling_queury.scalars().all()]
            self.polluters        = [Polluter_OO    (**el.__dict__) for el in polluters.scalars().all()]
            self.recyclers        = [Recycler_MNO   (**el.__dict__) for el in recyclers.scalars().all()]
            self.waste_categories = [WasteCategory  (**el.__dict__) for el in waste_categories.scalars().all()]
            



    def start(self):
        '''start the demon - it`ll be killed with main program on exit if u follow Usage guide'''
        self.demon_process.start()


    # release methods
    async def release_selected(self, wastes, deletion_session: AsyncSession):
        '''
        delete all selected waste-items from table
        !!! wastes - sqlalchemy-mapped Model, not pydentic
        deletion_session - session where "wastes" sqlalchemy-model was fetched from db 
        '''
        if type(wastes) == list:
            # batch of wastes
            for slot in wastes:
                await deletion_session.delete(slot)
                await deletion_session.commit()
        else: 
            # single waste
            await deletion_session.delete(wastes)
            await deletion_session.commit()

    async def release_waste_queury(self, moved_to_storage: list[PolluterWaste] | PolluterWaste):
        '''
        Release that waste-items from polluters_wastes` queury that were moved to recycling queury
        - moved_to_storage - list of polluter_wastes that were moved in storage 
        '''

        async with sessionFactory() as DeleteSession:
            # request corresponding sqlalchemy model to pydentic schema given in param
            # model must be binded to session to be operated - so the only way i see - is to select it from table (otherwise it errors)
            if type(moved_to_storage) == list:
                moved_to_storage_model = []    
                for waste in moved_to_storage:
                    model = await DeleteSession.execute(select(Models.PolluterWaste).where(Models.PolluterWaste.id == waste.id))
                    moved_to_storage_model.extend(model.scalars().all())
            else:
                model = await DeleteSession.execute(select(Models.PolluterWaste).where(Models.PolluterWaste.id == moved_to_storage.id))
                moved_to_storage_model = model.scalars().all()
            
            # finally pass this model(s) to release function
            await self.release_selected(moved_to_storage_model, DeleteSession)
            # and here release local instance - with original pydentic model
            self.PolluterWaste_DEL(moved_to_storage)


    async def release_recycling_queury(self):
        '''
        tldr: release recycling storage slots

        check recycling queury if there`s some wastes to release
        - if met wastes that has expired date => they`re recycled and storage slot is no longer occupied => release it 
        
        returns False if nothing to release
        '''
        now = datetime.now()
        ready_to_release = list(filter(lambda x: now >= x.release_time, self.recycling_queury))

        # convert pydentic schema to sqlalchemy model         
        async with sessionFactory() as DeleteSession:
            if ready_to_release:
                model_ready_to_release = []    
                for waste in ready_to_release:
                    model = await DeleteSession.execute(select(Models.RecyclerWaste).where(Models.RecyclerWaste.id == waste.id))
                    model_ready_to_release.extend(model.scalars().all())
            else:
                return False

            # TODO: cover bellow operations in transaction and rollback if fails

            # releasing all the storage-slots that are expired from DB
            await self.release_selected(model_ready_to_release, DeleteSession) 
            
            # Updating: return resources back to storages
            for slot in ready_to_release:
                old_slot = next(filter(
                    lambda x: x.recycler_id == slot.recycler_id and x.category == slot.category,
                    self.storage_slots))
                old_slot.amount_occupied -= slot.amount

                # same for DB
                await DeleteSession.execute(
                        update(Models.RecyclerStorage)
                        .where(
                            Models.RecyclerStorage.recycler_id == slot.recycler_id,
                            Models.RecyclerStorage.category == slot.category
                        )
                        .values(amount_occupied = old_slot.amount_occupied)) # already counted updated amount_occupied above 
                await DeleteSession.commit()

            # releasing all the storage-slots that are expired from Demon`s state
            self.RecyclerWaste_DEL(ready_to_release) 


    async def find_closest_storages(self, polluter_waste: PolluterWaste) -> list[tuple[RecyclerStorage, int]] | bool:
        '''
        find possible recycler-storage slots and range them by distance
        for given polluter_waste from wastes_queury (PolluterWastes)
        
        output: 
            list[(recycler, distance)] - in Asc BY distance
            or False - can`t find avaliable storages
        '''
        polluter_id = polluter_waste.polluter_id
        category    = polluter_waste.category

        # select recyclers storages that has free amount of space for needed category of wastes in storage
        possible_storages = list(filter(
            lambda x: x.category == category and x.amount_occupied < x.capacity,  # there`s avaliable space and needed category of waste
            self.storage_slots))
        
        if len(possible_storages) == 0:
            return False

        # find poluter`s (x, y) 
        polluter = next(filter(lambda x: x.id == polluter_id, self.polluters), None) 
        x, y = polluter.x_geo, polluter.y_geo

        # Look for needed distances in cache or count it and cache
        # reuse this values: store results in table with PK: polluter_id+recycler_id => sometimes distance counting will be O(1)
        cached_distances_ids = self.distances.keys() # get id of each counted distance | key = (polluter_id,recycler_id)        
        possible_storages_distances = [] 
        # [Warn] O(M*N) in memory usage - bad generally, but with not so great M and N it may be acceptable, also there may be compromises like giving limit to ammonunt of records in this simple "cache" and to rewrite some records with most used ones 
        for el in possible_storages:
            if (polluter_id, el.recycler_id) not in cached_distances_ids:
                recycler = next(filter(lambda x: x.id == el.recycler_id, self.recyclers)) # get recycler that owns current storage unit (el)

                self.distances[(polluter_id, el.recycler_id)] = pow(x - recycler.x_geo, 2) + pow(y - recycler.y_geo, 2)
            
            possible_storages_distances.append(
                (
                    el, # recycler
                    self.distances[(polluter_id, el.recycler_id)] # distance to recycler - takes from cache (self.distances)
                )  
            )

        return sorted(possible_storages_distances, key=lambda d: d[1])  # sort by distances => get distances starting with closest
        

    async def add_recycler_waste(self, recycler_id: UUID4, polluter_waste: Models.PolluterWaste, taken_amount: int):
        '''
        Helper-routine for move_from_wastes_to_storages()
        Warning - not supposed to be used directly 
        
        taken_amount - how much amount polluter waste can take fron recycler storage slot (counts in move_from_wastes_to_storages) 

        Add new item into RecyclerWaste 
        - table where accepted wastes are storing
        '''
        # get time to recycle for such waste
        time_to_recycle = next(
            filter(
                lambda x: x.category == polluter_waste.category, 
                self.waste_categories)
            ).time_to_recycle

        recycler_waste = Models.RecyclerWaste(
             amount=taken_amount,
             category=polluter_waste.category,
             recycler_id=recycler_id,
             release_time=datetime.now() + time_to_recycle
        )

        # Add recycler_waste to DB and Demon`s state
        async with sessionFactory() as addSession:
            # write new recycler_waste to DB
            addSession.add(recycler_waste)
            await addSession.commit()

            # UPDATE Demon`s state after DB was written - in pydentic !!!
            '''params = recycler_waste.__dict__
            # cast ids to str - to make pydentic and postgres CALM about UUID4 and str for id in different places - everywhere`ll be str
            params['id'] = str(recycler_waste.id)
            params['recycler_id'] = str(recycler_waste.recycler_id)'''

            self.RecyclerWaste_ADD(convert_to_pydentic(recycler_waste, RecyclerWaste))  


    async def move_from_wastes_to_storages(
            self, 
            polluter_waste: Models.PolluterWaste,                      # the waste from waste`s queury we want to recycle(move to recyclers` storage slots)
            closest_storages: list[tuple[Models.RecyclerStorage, int]] # possible recyclers` storage-slots ranged by distance <=> return of find_closest_storages()
        ):
        '''
        try moving specific waste from PolluterWaste to RecyclerWaste`s slot(s)
        - it`s possible that not all amount of waste is moved
        - otherwise here we create new RecyclerWaste item(s)

        SideEffect:
            cleaning waste_queue:
            if all amount of waste is moved - here we DELETE PolluterWaste item
        
        after possible recycler-storage slots were found and ranged by distance
        - here we can crawl through them and load data into them
        - this affects 3 tables:  PolluterWaste -> RecyclerStorage -> RecyclerWaste
        '''
        async with sessionFactory() as session_MOD:
            waste_idx = self.wastes_queury.index(polluter_waste)

            for storage, distance in closest_storages:
                storage_idx = self.storage_slots.index(storage)
                
                need = self.wastes_queury[waste_idx].amount
                free_space = storage.capacity - storage.amount_occupied
                
                delta = need - free_space 
                if delta < 0:
                    # free space is bigger than needed space
                    taken = need     
                else:
                    # take all avaliable free_space from storage - mb it`s not enough: need > free_space
                    taken = free_space 
                
                # Syncronize actual RecyclerStorage in DB with self.storage_slots
                self.storage_slots[storage_idx].amount_occupied += taken 
                await session_MOD.execute(
                    update(Models.RecyclerStorage)
                    .where(
                        # PK is complex
                        Models.RecyclerStorage.recycler_id == storage.recycler_id, 
                        Models.RecyclerStorage.category == storage.category)
                    .values(amount_occupied = self.storage_slots[storage_idx].amount_occupied))
                await session_MOD.commit()

                # same for PolluterWaste
                self.wastes_queury[waste_idx].amount -= taken 
                await session_MOD.execute(
                    update(Models.PolluterWaste)
                    .where(Models.PolluterWaste.id == polluter_waste.id)
                    .values(amount = self.wastes_queury[waste_idx].amount))
                await session_MOD.commit()

                # add new recycler_waste
                await self.add_recycler_waste(storage.recycler_id, polluter_waste, taken)

                # if all wastes were transfered to storages => delete waste from queue and exit
                if self.wastes_queury[waste_idx].amount == 0:
                    await self.release_waste_queury(polluter_waste) # delete waste from queue if it`s cleared
                    return
                    


    # Coroutins bellow works in conqurent async way in separate process - by multiprocessing
    async def main_loop(self):
        '''
        place where all recycler-demon`s actions happens constantly
        - it runs as separate proces - by multiprocessing
        '''
        await self.copy_DB() # load DB in Demon`s memory   
        
        # main loop
        while True:
            # listen to main.py if he has some commands that will deliver data (_ADD methods) to feed Demon`s in-memory tables (in atributes)
            self.listen_IPC_commands()
            # clean up storage-slots if it`s time - some wastes are mb already recycled
            if self.recycling_queury:
                await self.release_recycling_queury()

            # manage wastes from polluters
            if self.wastes_queury:
                for waste_cell in self.wastes_queury:
                    # find closest storages that can recycle such category of waste 
                    closest_storages = await self.find_closest_storages(waste_cell)

                    # moving wastes to possible storages preffering closests ones
                    if closest_storages:
                        await self.move_from_wastes_to_storages(waste_cell, closest_storages) 
                
                    '''with open('recycle_demon_logs', mode='a') as logs:
                        logs.write(f'\n RecyclerStorage now: {self.recycling_queury}\n')'''



    def listen_IPC_commands(self):
        '''
        method to listen calls to Demon (children) from main.py (parent)
        - so that batch of _ADD methods bellow are avaliable for parent process where API-methods sometimes feeds data to demon using IPC_queue
        '''    
        if not self.IPC_queue.empty():
            command = self.IPC_queue.get()

            if isinstance(command, tuple):
                # Expecting a tuple of (method_name, value)
                method_name, value = command

                method = getattr(self, method_name, None)
                if callable(method):
                    method(value)
                else:
                    print(f"Method {method_name} not found.")
        
                with open('recycle_demon_logs', mode='a') as logs:
                    logs.write(f'\nIPC-queue got command:\n {command}')
                    logs.write(f'\nLast polluter waste now: {self.wastes_queury[-1].__dict__}\n')
                    #logs.write(f'\nLast RecyclerStorage now: {self.storage_slots[-1].__dict__}\n')

    ''' 
    methods that are being used in IPC between Demon and main.py 
    Update in-memory attributes methods:
     ment to be used in app`s functions that changes (Add, Del, Modify) any of tables
      - to keep data in Demon up to date (stores in RAM)
    '''
    def Polluter_OO_ADD(self, new_item: Polluter_OO):
        self.polluters.append(new_item)
    def Recycler_MNO_ADD(self, new_item: Polluter_OO):
        self.recyclers.append(new_item)
    def RecyclerStorage_ADD(self, new_item: RecyclerStorage):
        self.storage_slots.append(new_item)


    def PolluterWaste_ADD(self, new_item: PolluterWaste):
        self.wastes_queury.append(new_item)
    def PolluterWaste_DEL(self, items):
        if type(items) == list:
            for el in items:
                self.wastes_queury.remove(el)
        else:
            self.wastes_queury.remove(items)

    def RecyclerWaste_ADD(self, new_item: RecyclerWaste):
        self.recycling_queury.append(new_item)
    def RecyclerWaste_DEL(self, items: list):
        if type(items) == list:
            for el in items:
                self.recycling_queury.remove(el)
        else:
            self.recycling_queury.remove(items)
