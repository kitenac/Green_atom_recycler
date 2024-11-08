from sqlalchemy import Column, ForeignKey, Integer, CHAR, VARCHAR, TIMESTAMP, Interval, NUMERIC, func, PrimaryKeyConstraint
from sqlalchemy.ext.declarative import declarative_base, declared_attr
from sqlalchemy.orm import relationship  # high level data access for related tables
import uuid
import inspect

import datetime

Base = declarative_base()


class Models:
    '''
    class-container for easy access to all existing model-classes
    via get_all_DB_models() method 
    '''
    @staticmethod
    def get_all_DB_models(): 
        '''
        get all DB`s tables` models:
            i.e all nested (inner) classes + that`re related to DB table
        '''
        return [ attr for attr in Models.__dict__.values() 
                 if inspect.isclass(attr) and hasattr(attr, '__tablename__') ]


    # common ploes for each table - AUTOGENERATED poles
    class CommonModel(Base):
        __abstract__ = True   # Class will not create table - just tamplate for other tables
        id = Column(CHAR(36), default=uuid.uuid4, primary_key=True)
        created_at = Column(TIMESTAMP, default=datetime.datetime.now())       # func - use some sql-function from database   
        updated_at = Column(TIMESTAMP, default=datetime.datetime.now(), onupdate=datetime.datetime.now())

    # common poles for organizations: OO and MNO 
    class CommonOrg(CommonModel):
        __abstract__ = True
        name  = Column(VARCHAR(64), nullable=False)
        
        # 2D-geo with 6 digets before and after comma 
        # - 12 digets in total, where 6 are for precision
        x_geo = Column(NUMERIC(12,6, asdecimal=False), nullable=False)  # asdecimal=False - permits floats as value without casting to Decimal type
        y_geo = Column(NUMERIC(12,6, asdecimal=False), nullable=False)

        def __str__(self):
            return self.name
        
    # excisting MNO and OO
    class Polluter_OO(CommonOrg):
        __tablename__ = 'Polluter_OO'
    class Recycler_MNO(CommonOrg):
        __tablename__ = 'Recycler_MNO'


    # waste categories
    class WasteCategory(CommonModel):
        __tablename__ = 'WasteCategory'
        id = None # exclude common PK - here it`s different PK - category
        
        category = Column(VARCHAR(32), primary_key=True, nullable=False) # uniqness off waste competly relys on it`s name (unlike organizations that may have common names)
        time_to_recycle = Column(Interval, nullable=False)            # usage:  datetime.timedelta(hours=152, minutes=21) | how much it takes to recycle this waste
        
        def __str__(self):
            return self.category

    # total storage size of each type of waste for each Recycler: 
    # u can think of each record in this table <=> storage-slot for some category of waste belonging to particular Recycler 
    class RecyclerStorage(CommonModel):
        __tablename__ = 'RecyclerStorage'
        id = None # exclude common PK
        # pair of FK is a PK in storage
        __table_args__ = (PrimaryKeyConstraint('recycler_id', 'category'),)
        recycler_id = Column(CHAR(36), ForeignKey('Recycler_MNO.id'), primary_key=True)
        category    = Column(VARCHAR(32), ForeignKey('WasteCategory.category'), primary_key=True)
        
        capacity = Column(Integer, nullable=False) # total capacity of Recycler
        amount_occupied = Column(Integer, default=0) # total size of recived wastes


        # relationships for pretty graph (with directed arrows)
        recycler      = relationship('Recycler_MNO')
        WasteCategory = relationship('WasteCategory')



    # info about each waste holding at OO and MNO queuries:
    # TODO somehow store wastes of common type together - to reduce utilization (mb Mongo - it`s good for itterables) 
    class WasteInfo(CommonModel):
        __abstract__ = True
        amount      = Column(Integer, default=0)
        category    = Column(VARCHAR(32), ForeignKey('WasteCategory.category'))

        # define relationship in abstract class
        @declared_attr
        def WasteCategory(cls):
            return relationship('WasteCategory')

    class PolluterWaste(WasteInfo):
        __tablename__ = 'PolluterWaste'
        polluter_id = Column(CHAR(36), ForeignKey('Polluter_OO.id')) 
        polluter = relationship('Polluter_OO')

    class RecyclerWaste(WasteInfo):
        __tablename__ = 'RecyclerWaste'
        recycler_id  = Column(CHAR(36), ForeignKey('Recycler_MNO.id'))
        release_time = Column(TIMESTAMP)   # counts as: CURRENT_TIME + WasteCategory.time_to_recycle
        recycler = relationship('Recycler_MNO')