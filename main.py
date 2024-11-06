'''
Project structure:

app - common and general stuff
- schemas for API-response, db config, etc

poluter_OO - everything sufficient about organizations that creates wastes
recycer_MNO - same but for recyclers


OO --> MNO  <=> producer --> consumer

'''
from app.setup_app import start_app
from recycler_demon.demon import RecyclerDemon

from demon_main_IPC import IPC_queue # way to communicate with Demon

# demon process to handle wastes
My_RecyclerDemon = RecyclerDemon(IPC_queue) 

if __name__ == "__main__":
  try:    
    # start the Demon process to handle wastes
    My_RecyclerDemon.start()
    
    # start the app
    start_app()
  finally:
    # if the app was broken/exited - terminate demon process - not to allow zombies 
    My_RecyclerDemon.demon_process.terminate()

