
нужно для отрисовки графа БД:

sudo apt-get install graphviz
sudo apt-get install --reinstall xdg-utils


# Уже не нужно
for entities graphs:
sudo apt-get install libbz2-dev 

than reinstall current python version (3.12.1 in my case)
bc python can`t see libbz2-dev without reinstalation: https://stackoverflow.com/questions/27727919/pythonbrew-importing-bz2-yields-importerror-no-module-named-bz2
- pyenv uninstall 3.12.1
- pyenv install 3.12.1
# Уже не нужно


sudo pip install -r req.txt

ENV настроить в контейнере постгрес
POSTGRES_PASSWORD = root
POSTGRES_USER = root


# mocking tables with data:
python3 mock_tables.py