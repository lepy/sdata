from typing import Dict, Set, List, Iterable, TypeVar, Hashable

T = TypeVar('T', bound=Hashable)


class CircularDependencyError(ValueError):
    """Exception raised when circular dependencies are detected during topological sort."""

    def __init__(self, remaining_graph: Dict[T, Set[T]]):
        message = (
            "Circular dependencies exist among these items: "
            f"{{{', '.join(f'{key}: {sorted(value)}' for key, value in sorted(remaining_graph.items()))}}}"
        )
        super().__init__(message)
        self.remaining_graph = remaining_graph


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


def toposort_flatten(graph: Dict[T, Iterable[T]], sort: bool = True) -> List[T]:
    """Flatten the topological sort into a single list.

    This function consumes the generator from toposort() and appends the nodes
    from each level to a list. If sort is True, nodes within each level are sorted
    for deterministic order.

    Args:
        graph: A dictionary representing the dependency graph.
        sort: Whether to sort nodes within each topological level (default: True).

    Returns:
        A list of nodes in topological order.

    Raises:
        CircularDependencyError: If a cycle is detected in the graph.
    """
    result: List[T] = []
    for level in toposort(graph):
        result.extend(sorted(level) if sort else list(level))
    return result
