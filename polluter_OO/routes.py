from fastapi import APIRouter, HTTPException, Depends, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

 
from app.db import get_db_session
from app.models import Models
from app.schemas import *
from app.response_statuses import common_status_resolver, common_statuses, category_checker

from demon_main_IPC import send_command_to_demon # way to notify demon that there`re new entities in DB

router = APIRouter(prefix='/polluter')


# Create pollutor
@router.post('', status_code=201, summary='add polluter-organization')
async def create_polutor(
    name: str = Body(), 
    x_geo: float = Body(),
    y_geo: float = Body(),
    SessionLocal: AsyncSession = Depends(get_db_session)
):
    polluter = Models.Polluter_OO(name=name, x_geo=x_geo, y_geo=y_geo)
    SessionLocal.add(polluter)
    await SessionLocal.commit()
    
    send_command_to_demon('Polluter_OO_ADD', Polluter_OO(**polluter.__dict__))  # feed the demon new data
    return API_Response(
        **common_statuses[201]['CREATED'],
        code=201
    )


# Add wastes to PlluterWastes queue
@router.post('/{polluter_id}/wastes', summary='add some waste of polluter to queue')
async def add_polluter_wastes(
   polluter_id:  str,
   amount:       int = Body(), 
   category:     str = Body(), 
   SessionLocal: AsyncSession = Depends(get_db_session)
):
    ''' Tell that polluter organization has new waste of some category and ammont - recycler will watch this queue '''
    
    category_checker(category) # check if chosen category excists, otherwise - HTTPException 409

    polluter_waste = Models.PolluterWaste(
        polluter_id = polluter_id,
        category    = category,
        amount      = amount
    )

    SessionLocal.add(polluter_waste)
    await SessionLocal.commit()

    send_command_to_demon('PolluterWaste_ADD', PolluterWaste(**polluter_waste.__dict__))
    return API_Response(
        **common_statuses[201]['CREATED'],
        code=201
    )



# Read
@router.get('', status_code=200, summary='get all polluter-organizations')
async def get_all_recyclers(
    SessionLocal: AsyncSession = Depends(get_db_session)
):
    polluters = await SessionLocal.execute(select(Models.Polluter_OO))
    polluters = polluters.scalars().all()
    data = [Polluter_OO(**el.__dict__) for el in polluters] # TODO: find different neet way to fill pydentic models, due uncpacking as dictionary mb dirty

    return API_Response(
        **common_status_resolver(data),
        code=200,
        data=data, 
        meta=API_Response.MetaData(
            total=len(polluters)
        ))



'''# Upadte
@router.put('/{polluter_id}', summary='try to clear all wastes from')
async def clear_wastes(polluter_id: str):
    
    Попытаться очистить ОО от всех отходов

    !!! Тут ОО обязан посылать отходы в таком составе - который точно поместится в МНО 
    - елси не выйдет - МНО вернёт 400 (/recycler/{polluter_id})

    Возвращает число оставшихся отходов после очистки (не всегда получится найти МНО, чтоб отходы переработать)

    
    
    # !!! TODO: ОБЯЗАТЕЛЬНО определи условие, что места нет - ниже - мб обернуть в try/except
    if ('НЕ ПОЛУЧИЛОСЬ НАЙТИ СКЛАДЫ, ЧТОБ ВСЁ ЧТО ПРОСИЛИ УМЕСТИТЬ'):

        status, details = statuses[400]['NOT_ENOUGH_SPACE'].values()
        # - 400 возвращать, если не получается обработать отходы в том составе, котором указал ОО (почему - смотри док стринг)        
        raise HTTPException(status_code=400, detail=details, status=status)
        

    pass    '''