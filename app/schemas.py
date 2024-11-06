from pydantic import BaseModel, Field, UUID4
from typing import Optional, Dict, Annotated
from datetime import timedelta, datetime   # for Interval type


# ======= Response =======
# API response template
class API_Response(BaseModel):
    class MetaData(BaseModel):
       total: int = 0
       TODO: str = 'metadata here'

    # actual data from Data base:
    data: list[object] = []
    # metadata about data (for pagination)
    meta: MetaData = Optional[Dict]
    # some request info:
    status: str = 'not implemented' # code-word to identify response from API | why? - 400 code may be caused by several reasons - so status-code-word clarifies the reason of 400-code
    details: Optional[str] = ''         # details about status | see response_details.py  | for ex explain why client gets 400-code and how to fix it 
    error_values: Optional[object] = []       # exact values that caused an exception
    code: int = 0             
   


# ==== Tables

# common poles for each table
class CommonTable(BaseModel):
   # auto generated poles - so make `em optional (by None)
   id: Optional[str] = None
   created_at: Optional[datetime] =  None
   updated_at: Optional[datetime] =  None

class CommonOrg(CommonTable):
   name: str = Field(..., max_length=64) 
   x_geo: float
   y_geo: float

# just inherit 
class Polluter_OO(CommonOrg):
   pass
class Recycler_MNO(CommonOrg):
   pass

class RecyclerStorage(CommonTable):
   recycler_id: Annotated[str, 'id of Recycler'] = Field(..., length=36)
   category:    Annotated[str, "биоотходы | стекло | пластик"] = Field(..., length=32)
        
   capacity: int        # total capacity of Recycler
   amount_occupied: Optional[int] = 0 # total size of recived wastes

    # add support for orm`s objects - by poles (in pydentic - by keys):
   #   in orm:      id = data.id
   #   in pydentic: id = data['id']  
   class Config:
     from_attributes = True

class WasteInfo(CommonTable):
   amount: int 
   category: str = Field(..., max_length=32) 

class PolluterWaste(WasteInfo):
   polluter_id: str = Field(..., length=36)
   

class RecyclerWaste(WasteInfo):
   recycler_id: str = Field(..., length=36)
   release_time: datetime

class WasteCategory(CommonTable):
   created_at: Optional[datetime] =  None
   updated_at: Optional[datetime] =  None

   category: str
   time_to_recycle: timedelta