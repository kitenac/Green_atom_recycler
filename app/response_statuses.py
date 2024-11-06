'''
Setting up info for HHTP codes:

    Status - code-word 
    Detailes - clarification of Staus
'''
from fastapi import HTTPException

common_statuses = {
    200: {
        'OK': {
            'status': 'OK',
            'details': 'all right'
        }
    },
    201: {
        'CREATED':
        {
            'status': 'OK',
            'details': 'entity created'
        }
    },
    204: {
        'OK_EMPTY_DATA': {
            'status': 'OK_EMPTY_DATA',
            'details': 'accepted request, but there`s no matching data in table to return'
        }
    }
}

def common_status_resolver(data) -> dict:
    ''' return dictionary of status_code and details'''
    if len(data) == 0:
        return common_statuses[204]['OK_EMPTY_DATA']
    
    return common_statuses[200]['OK']

def category_checker(category: str):
    '''Throws HTTP exception when chosen category doesn`t excists'''
    avaliable_categorirs = ['биоотходы', 'стекло', 'пластик']
    if category not in avaliable_categorirs:
        raise HTTPException(409, detail={
            'body_params_dict': recycler_statuses[409]['CONFLICT_WasteCategory'],
            'error_values': f'{category}'
        })   




recycler_statuses = {
    400: {
        'NOT_ENOUGH_SPACE': {
            'status': 'NOT_ENOUGH_SPACE',
            'details': 'Required wastes configuration can`t be accepted by chosen Recycler. Check avaliable storage space for each type of waste in chosen Recycler'
        },
    },
    409: {
        'CONFLICT_PK': {
            'status': 'CONFLICT_PK',
            'details': 'Chosen combination of PK-s: waste_category, recycler_id - already excists!'
        },
        'CONFLICT_WasteCategory': {
            'status': 'CONFLICT_WasteCategory',
            'details': 'Chosen WasteCategory doesn`t excists!'
        }
    }
}


polluter_statuses = {
    200: {
        'OK': {
            'status': 'OK',
            'details': 'all right'
        }
    }
}