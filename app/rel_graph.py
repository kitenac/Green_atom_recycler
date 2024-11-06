'''
    Generating graph of entities` relations to vizualize their connections
'''

import networkx as nx
from matplotlib import pyplot as plt
from typing import Iterable

class EntityRelations:
    '''
        Class to vizualize entities relationships
    '''

    def __init__(self, G=nx.Graph()):
        '''graph-based relations'''
        self.G = G

    def build_graph(self, nodes: Iterable[str], edges: Iterable[Iterable[str]]):
        '''
        example:
            nodes = ["Table A", "Table B", "Table C", "Table D"]
            edges = (   ("Table A", "Table B"), ("Table B", "Table C")  )
        '''
        self.G.add_nodes_from(nodes)
        self.G.add_edges_from(edges)
    
    def draw_graph(self, image_name='graph', title='entities graph'):
        ''' Draw the graph '''
        plt.title(title)
        plt.figure(figsize=(10, 6))
        nx.draw(self.G, with_labels=True, node_color='lightblue', node_size=3000, font_size=12, font_color='black', font_weight='bold', edge_color='gray')
        
        # Save the graph as an image
        plt.savefig(f'{image_name}.png')
        plt.close()  # Close the plot to free memory    
        
if __name__ == "__main__":
    nodes = ["Table A", "Table B", "Table C", "Table D"]
    edges = (   
        ("Table A", "Table B"),
        ("Table B", "Table C"),
        ("Table C", "Table D"),
        ("Table D", "Table A")  
    )

    TablesRlations = EntityRelations()
    TablesRlations.build_graph(nodes, edges)
    TablesRlations.draw_graph(image_name='test-relations')
