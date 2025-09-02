import logging
from typing import Dict, Type, List, Union

from sdata.sclass.process import ProcessNode, CompositeProcess


try:
    import graphviz
except ImportError as e:
    logging.warning("graphviz not available.")
    graphviz = None


class ProcessGraph:
    def __init__(self):
        self.data_nodes = set()
        self.process_nodes = set()
        self.edges = []
        self.class_map: Dict[str, Type[ProcessData]] = {}
        self.process_class_map: Dict[str, Union[Type[ProcessNode], Type[CompositeProcess]]] = {}

    def add_process(self, process_class: Union[Type[ProcessNode], Type[CompositeProcess]]):
        proc_name = process_class.__name__ if hasattr(process_class, '__name__') else process_class.name
        self.process_nodes.add(proc_name)
        self.process_class_map[proc_name] = process_class

        # Instantiate a dummy to get attributes, as composites set them in __init__
        dummy = process_class(inputs=None)  # Use inputs=None for dummy
        input_classes = dummy.input_classes
        output_classes = dummy.output_classes
        # computation = dummy.computation  # Not needed here, but for consistency

        for input_name, input_class in input_classes.items():
            self.data_nodes.add(input_name)
            self.class_map[input_name] = input_class
            self.edges.append((input_name, proc_name))

        for output_name, output_class in output_classes.items():
            self.data_nodes.add(output_name)
            self.class_map[output_name] = output_class
            self.edges.append((proc_name, output_name))

    def to_graphviz(self, name="SumSquare", rankdir="TD", collapsed=True):
        dot = graphviz.Digraph(name=name, graph_attr={'rankdir': rankdir})

        for data in self.data_nodes:
            cls = self.class_map[data]
            # fields = [attr['name'] for attr in cls.default_attributes if 'name' in attr]
            label = '{' + data + '}'
            dot.node(data, shape='record', label=label)

        for proc in self.process_nodes:
            proc_class = self.process_class_map[proc]
            # Instantiate dummy to get computation
            label = '{' + proc + '}'
            dot.node(proc, shape='record', label=label)

        for src, dst in self.edges:
            dot.edge(src, dst)

        return dot