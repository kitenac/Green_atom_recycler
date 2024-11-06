# DB schema:
![Logo](data_model_diagram.svg)

# About Demon and muliprocessing
App/backend - parent\
RecyclerDemon - child\
RecyclerDemon stores db in memory and manages waste redestribution and recycling (deletes wastes from recycler storage slots when it`s time)\
RecyclerDemon - loads DB only once - when runned\
than App gives updated data to Recycler_Demon through IPC-queury of commands - feeds demon updates\

Also RecyclerDemon maintanes and populates cache with distances between pollutors and recyclers, btw distances stores squared (not to count radical - just to have ability to range avaliable recyclers by distance) \
 
The DB Table RecyclerWastes (queue of wastes being recycled in recycler\`s storage slots) - fully under Demon`s controll, no one else modifies it

# Frontend-like admin-page
- admin page is buggy, but works fine as frontend to monitor entities
- to generate entities - use mock (see section bellow)
http://127.0.0.1:8001/api/v1.0/admin/

# Docs
http://127.0.0.1:8001/docs

# Mocking tables with data:
python3 mock_tables.py
- also will be api mock-methods to add some random wastes or recyclers

# Draw graph of DB:
from repo`s folder run:
- python3 -m db-visualizer.db-visualizer

# Required packages
for drawing grah of DB:
- sudo apt-get install graphviz
- sudo apt-get install --reinstall xdg-utils



# \[Experimental/for-future\] Rendering graphs:
i`ve managed to constract suitable api for visualazing relationships between objects
- maby in future i`ll find some usecases for it - see app.rel_graph.py

Requirments to use it:
- apt-get install libbz2-dev 

than reinstall current python version (3.12.1 in my case)\
bc python can`t see libbz2-dev without reinstalation: https://stackoverflow.com/questions/27727919/pythonbrew-importing-bz2-yields-importerror-no-module-named-bz2
- pyenv uninstall 3.12.1
- pyenv install 3.12.1

now app/rel_graph.py should work fine (it`s API can be used from mocks or some route)
python3 app/rel_graph.py 




