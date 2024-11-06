'''
IPC related staff for main.py and recycling_demon
'''
import multiprocessing

IPC_queue = multiprocessing.Queue()

def send_command_to_demon(method: str, val: object):
    ''' Send tupple with disered metod and value into demon process 
    - demon will listen it in self.listen_IPC_commands
    
    Example:
    in route for creating new Polluter_OO:
        send_command_to_demon('Polluter_OO_ADD', polluter)
    '''
    IPC_queue.put(
        (method, val)
    )
