'''
 cool admin-page - eazy CRUD through db
    docs: https://aminalaee.dev/sqladmin/ 
'''
from sqladmin import Admin, ModelView
# docs: https://aminalaee.dev/sqladmin/configurations/

from app.db import engine, sessionFactory
from app.patch_admin_lib import patch_datetime 

patch_datetime() # patching sqladmin to fix render failure of datetime


# ====[START]==== Config models to be displayed at admin page ====[START]====
from app.models import Models


models = Models.get_all_DB_models()

#print(*models[2].__table__.columns.keys(), sep='\n')

def create_admin_page(app):
    '''
        Creating app with admin page avaliable at 
        API_URL/admin

        usage: 
            admin = create_admin_page(name_app)
            admin.mount_to(app=name_app)
    
        TODO: auth
    '''
    
    admin = Admin(app, engine=engine, session_maker=sessionFactory, title=f"Admin page | {app.title}")



    def gen_ModelView(model):
        '''
        Create view-class for sqladmin dynamically by given model
        '''
        class Model_view(ModelView, model=model):
            column_list = "__all__" # special flag to include all cols - same as [column for column in model.__table__.columns.keys()] # [getattr(model, column) for column in model.__dict__ if not column.startswith('_')]
            form_columns = column_list
        return Model_view

    for model in models:        
        admin.add_view(gen_ModelView(model)) 
    
    return admin