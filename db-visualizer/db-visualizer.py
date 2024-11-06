'''
 cool lib to visualize sqlalchemy models and their relationships

 !!! нужно доустановить для отрисовки графа БД:
        sudo apt-get install graphviz
        sudo apt-get install --reinstall xdg-utils


запуск из корня репозитория:
 python3 -m db-visualizer.db-visualizer
                
'''


''' params:
- models: List of SQLAlchemy models you want to visualize.
- output_file: Name of the output SVG file.
- add_labels: Set to False to hide labels on the edges between tables '''

from app.models import Models
# tricky lib-import, due lib is unrecognized after installation 
# - also in this file u can redo the way tables-schema is displayed: colors, widths and other 
from sqlalchemy_data_model_visualizer import generate_data_model_diagram, add_web_font_and_interactivity


models = Models.get_all_DB_models()
file_name = 'data_model_diagram'

# regular svg diagram
generate_data_model_diagram(models, output_file=file_name, add_labels=True)

# interactive one
add_web_font_and_interactivity(f'{file_name}.svg', f'interactive_{file_name}.svg')




