from fastapi import APIRouter, HTTPException, Depends, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select

from app.db import get_db_session
from app.models import Models
from app.schemas import *
from app.response_statuses import common_status_resolver, common_statuses, recycler_statuses, category_checker

from demon_main_IPC import send_command_to_demon # way to notify demon that there`re new entities in DB

router = APIRouter(prefix='/recycler')



@router.post('', status_code=200, summary='cretate new recycler')
async def create_recycler(
    name: str = Body(), 
    x_geo: float = Body(),
    y_geo: float = Body(),
    SessionLocal: AsyncSession = Depends(get_db_session)
):
    '''
    cretate new recycler
    '''
    recycler = Models.Recycler_MNO(name=name, x_geo=x_geo, y_geo=y_geo)
    SessionLocal.add(recycler)
    await SessionLocal.commit()

    send_command_to_demon('Recycler_MNO_ADD', Recycler_MNO(**recycler.__dict__))
    return API_Response(
        **common_statuses[201]['CREATED'],
        code=201
    )
        

# add new storage for wastes of specific type for specific rcycler 
@router.post('/{recycler_id}/storage', status_code=201, summary='Add a new storage slot for wastes in Recycler')
async def add_recycler_storage_slot(
   recycler_id:     Annotated[str, 'id of Recycler'],
   category:        Annotated[str, "биоотходы | стекло | пластик"] = Body(),
   capacity:        int = Body(),  # total capacity of Recycler
   amount_occupied: Optional[int] = Body(),  # total size of recived wastes
   SessionLocal:    AsyncSession = Depends(get_db_session)
):
    ''' Add a new storage slot for wastes of specific type for specific recycler '''
    
    category_checker(category) # check if chosen category excists, otherwise - HTTPException 409
    
    try:
        recycler_storage_slot = Models.RecyclerStorage(
            recycler_id     = recycler_id,
            category        = category,
            capacity        = capacity,
            amount_occupied = amount_occupied
        )
        SessionLocal.add(recycler_storage_slot)
        await SessionLocal.commit()

        send_command_to_demon('RecyclerStorage_ADD', RecyclerStorage(**recycler_storage_slot.__dict__))
        return API_Response(
        **common_statuses[201]['CREATED'],
        code=201)

    # This exception will be handled in setup_app`s middleware and create API_Response with provided info from recycler_statuses
    except IntegrityError as e:        
        raise HTTPException(status_code=409, detail={
            'body_params_dict': recycler_statuses[409]['CONFLICT_PK'],
            'error_values': f'recycler_id: {recycler_id}, wastecategory: {category}'
        })

    
# Read
@router.get('', status_code=200, summary='get all recyclers')
async def get_all_recyclers(
    SessionLocal: AsyncSession = Depends(get_db_session)
):
    '''
    get a list of all recyclers 
    '''
    recyclers = await SessionLocal.execute(select(Models.Recycler_MNO))
    recyclers = recyclers.scalars().all()
    data = [Polluter_OO(**el.__dict__) for el in recyclers] # TODO: find different neet way to fill pydentic models, due uncpacking as dictionary mb dirty

    return API_Response(
        **common_status_resolver(data),
        code=200,
        data=data, 
        meta=API_Response.MetaData(
            total=len(recyclers)
        ))

'''
# Upadte
# TODO - загуглить нормальный мок, чтоб к докер-образу потом автозаполнение было 
@router.put('/{recycler_id}')
async def accept_wastes(recycler_id: str):
    
    Тут МНО обрабатывает запрос от ОО со списком отходов 
    - ОО обязан посылать отходы в таком составе - который точно поместится в МНО 
    - иначе 400 вернём (чтоб согласованность не нарушать - клиент должен иметь гарантию, что его запрос в полном объёме выполнится, а не в произвольном - иначе его планы могут сорваться: просил 50 пластика принять, а МНО "решило" ему только 10 дать)
    
    
    # !!! TODO: ОБЯЗАТЕЛЬНО определи условие, что места нет - ниже - мб обернуть в try/except
    if ('НЕ ХВАТАЕТ МЕСТА'):

        status, details = statuses[400]['NOT_ENOUGH_SPACE'].values()
        # - 400 возвращать, если не получается обработать отходы в том составе, котором указал ОО (почему - смотри док стринг)        
        raise HTTPException(status_code=400, detail=details, status=status)
        

    pass    '''
