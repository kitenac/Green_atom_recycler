'''
here we connect all parts of application to make it work:
routes,
middleware,
db sessions,
etc
'''

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn # server engine
from app.admin_page import create_admin_page

import logging
from . import schemas # data schemas

# routes - like mini-apps  
from recycler_MNO.routes import router as routes_MNO
from polluter_OO.routes import router as routes_OO 


# ==== HTTP App configuration
# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# App settings
API_BASE = '/api/v1.0'
atom_eco_app = FastAPI(root_path=API_BASE, title='Atom-ECO')

# CORS - настройка разрешённых ресурсов сервера
CORS_conf = {
  'origins': ['*'],  #  разрешённые адреса клиентов 
  'allow_creds': True,   # Разрешить отправку учётных данных
  'methods': ['*'],   # GET, POST, ...
  'headers': ['*']    # Accept, Content-Type, Referer, Content-Length ...
}

# Добавим middleware для CORS
atom_eco_app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_conf['origins'],     
    allow_credentials=CORS_conf['allow_creds'],   
    allow_methods=CORS_conf['methods'],     
    allow_headers=CORS_conf['headers'],     
    
)


# URL prefixes handlers 
# - like mini-apps for each url-prefix  
atom_eco_app.include_router(routes_MNO) 
atom_eco_app.include_router(routes_OO) 


# Mount the admin page app to main app - /admin
admin = create_admin_page(atom_eco_app)
atom_eco_app.mount(app=admin, path='/admin')


# ====  HTTPException handling
# TODO: upgrade, mb
@atom_eco_app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, e: HTTPException):
    return JSONResponse(
        status_code=e.status_code,
        
        content=schemas.API_Response(
          code = e.status_code, 
          error_values = e.detail['error_values'],   # exact vvalues that caused an exception
          **e.detail['body_params_dict']             # some POST body params that tells about occured exception
        ).model_dump()
    )


def start_app():
    uvicorn.run(atom_eco_app, host="0.0.0.0", port=8001)