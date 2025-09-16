import logging
from typing import Dict, Type, List, Union, Iterable, TypeVar, Hashable, Set

T = TypeVar('T', bound=Hashable)

from sdata.sclass.process import ProcessNode, CompositeProcess


try:
    import graphviz
except ImportError as e:
    logging.warning("graphviz not available.")
    graphviz = None

class CircularDependencyError(ValueError):
    """Exception raised when circular dependencies are detected during topological sort."""

    def __init__(self, remaining_graph: Dict[T, Set[T]]):
        message = (
            "Circular dependencies exist among these items: "
            f"{{{', '.join(f'{key}: {sorted(value)}' for key, value in sorted(remaining_graph.items()))}}}"
        )
        super().__init__(message)
        self.remaining_graph = remaining_graph

class ProcessGraph:
    def __init__(self, processes: List[ProcessNode] = None, name: str = "ProcessGraph"):
        self.name = name
        self.data_nodes = set()
        self.process_nodes = set()
        self.edges = []
        self.class_map: Dict[str, Type[ProcessData]] = {}
        self.process_class_map: Dict[str, Union[Type[ProcessNode], Type[CompositeProcess]]] = {}
        if processes is None:
            processes = []
        self.processes: List[ProcessNode] = processes
        for process in self.processes:
            self.add_process(process)

    def get_dependencies(self):
        dependencies = {}
        for process in self.processes:
            d = process.get_dependencies()
            dependencies.update(d)
        return dependencies

    def get_subprocess_graph(self):
        sg = self.__class__(name="subprocessgraph")
        for p in self.processes:
            for sp in p.processes:
                sg.add_process(sp)
        return sg

    def get_dag(self, flatten=False, sort: bool = True):
        dag = self.toposort(self.get_dependencies())
        if flatten:
            dag_flat: List[T] = []
            for level in dag:
                dag_flat.extend(sorted(level) if sort else list(level))
            return dag_flat
        else:
            return dag


    def __str__(self):
        return f"<{self.__class__.__name__}:proc={len(self.process_nodes)}:data={len(self.data_nodes)}>"

    __repr__ = __str__

    def add_process(self, process_class: Union[Type[ProcessNode], ]):
        self.proc_name = proc_name = process_class.__name__ if hasattr(process_class, '__name__') else process_class.name
        self.process_nodes.add(proc_name)
        self.process_class_map[proc_name] = process_class

        self.processes.append(process_class)

        # Instantiate a dummy to get attributes, as composites set them in __init__
        dummy = process_class(inputs=None)  # Use inputs=None for dummy
        self.input_classes = input_classes = dummy.input_classes
        self.output_classes = output_classes = dummy.output_classes
        # computation = dummy.computation  # Not needed here, but for consistency


        for input_name, input_class in input_classes.items():
            self.data_nodes.add(input_name)
            self.class_map[input_name] = input_class
            self.edges.append((input_name, proc_name))

        for output_name, output_class in output_classes.items():
            self.data_nodes.add(output_name)
            self.class_map[output_name] = output_class
            self.edges.append((proc_name, output_name))

    def update_class_map(self):
        self.data_nodes = set()
        self.process_nodes = set()
        self.edges = []
        self.class_map: Dict[str, Type[ProcessData]] = {}

        for input_name, input_class in self.input_classes.items():
            self.data_nodes.add(input_name)
            self.class_map[input_name] = input_class
            self.edges.append((input_name, self.proc_name))

        for output_name, output_class in self.output_classes.items():
            self.data_nodes.add(output_name)
            self.class_map[output_name] = output_class
            self.edges.append((self.proc_name, output_name))

    def to_graphviz(self, name: str = None, rankdir="TD", collapsed=True):
        if name is None:
            name = self.name
        dot = graphviz.Digraph(name=name, graph_attr={'rankdir': rankdir})

        for data in self.data_nodes:
            data_cls = self.class_map[data]
            label = data_cls.__name__
            dot.node(data, shape='box', label=label)

        for proc in self.process_nodes:
            proc_cls = self.process_class_map[proc]
            # Instantiate dummy to get computation
            label = proc_cls.__name__
            dot.node(proc, shape='component', label=label, color="lightblue", style="filled")

        for src, dst in self.edges:
            dot.edge(src, dst)

        return dot

    def to_graphviz_cluster(self, name: str = None, rankdir="TD", collapsed=True):

        g = graphviz.Digraph(name=name, graph_attr={'rankdir': rankdir})

        sg = self.get_subprocess_graph()

        # Cluster-Subgraph als Box erstellen
        with g.subgraph(name='cluster_use_eol') as cluster:
            # Attribute für die Box setzen
            cluster.attr(label=self.name, style='filled', color='black', peripheries='1', penwidth='1.5',
                         fillcolor='#efffff', labelloc="t", labeljust="l")

            for data in sg.data_nodes:
                if data not in self.data_nodes:
                    data_cls = sg.class_map[data]
                    label = data_cls.__name__
                    cluster.node(data, shape='box', label=label)

            for proc in sg.process_nodes:
                proc_cls = sg.process_class_map[proc]
                # Instantiate dummy to get computation
                label = proc_cls.__name__
                cluster.node(proc, shape='component', label=label, color="lightblue", style="filled")

            for data in self.data_nodes:
                data_cls = self.class_map[data]
                label = data_cls.__name__
                g.node(data, shape='box', label=label)

            for src, dst in sg.edges:
                if src not in self.input_classes and src not in self.output_classes and dst not in self.input_classes and dst not in self.output_classes:
                    cluster.edge(src, dst)
                else:
                    g.edge(src, dst)

        return g

    @staticmethod
    def toposort(graph: Dict[T, Iterable[T]]) -> Iterable[Set[T]]:
        """Perform a topological sort on a directed acyclic graph (DAG).

        Dependencies are expressed as a dictionary where keys are nodes and values are
        iterables of dependent nodes (nodes that the key depends on). The output is a
        generator yielding sets of nodes in topological order. The first set contains
        nodes with no dependencies, and each subsequent set contains nodes that depend
        only on nodes in preceding sets.

        If the graph contains cycles, a CircularDependencyError is raised.

        Args:
            graph: A dictionary representing the dependency graph.

        Yields:
            Sets of nodes in topological order.

        Raises:
            CircularDependencyError: If a cycle is detected in the graph.
        """
        if not graph:
            return

        # Create a copy of the graph, converting dependencies to sets and removing self-dependencies.
        graph = {node: set(dep for dep in deps if dep != node) for node, deps in graph.items()}

        # Identify nodes that appear only as dependencies (no outgoing edges defined).
        extra_nodes = {dep for deps in graph.values() for dep in deps} - set(graph)
        graph.update({node: set() for node in extra_nodes})

        while True:
            # Find nodes with no remaining dependencies.
            independent_nodes = {node for node, deps in graph.items() if not deps}
            if not independent_nodes:
                break
            yield independent_nodes
            # Remove processed nodes from the graph.
            graph = {
                node: (deps - independent_nodes)
                for node, deps in graph.items()
                if node not in independent_nodes
            }

        if graph:
            raise CircularDependencyError(graph)

def get_process_graph(processes: List[Type[ProcessNode]]) -> ProcessGraph:
    g = ProcessGraph()
    for process in processes:
        g.add_process(process)
    dot_graph = g.to_graphviz(name="CombinedProcess", rankdir="TD", collapsed=True)
    return dot_graph

