"""
Utility functions for dynamic module importing and dependency management.

This module provides helper utilities, particularly for dependency
resolution and graph algorithms used in module lifecycle management.
"""

from __future__ import annotations

from collections import defaultdict, deque
from typing import Dict, Generic, List, Optional, Set, TypeVar

from .exceptions import CircularDependencyError

T = TypeVar("T")


class DependencyGraph(Generic[T]):
    """
    Graph data structure for managing dependencies and their resolution order.

    This class provides topological sorting algorithms to handle module
    dependencies for initialization and teardown procedures.

    Time Complexity:
        - Addition of nodes and edges: O(1)
        - Topological sort: O(V + E) where V is number of nodes and E is number of edges
    """

    def __init__(self) -> None:
        """Initialize an empty dependency graph."""
        self.graph: Dict[T, List[T]] = defaultdict(list)
        self.nodes: Set[T] = set()

    def add_node(self, node: T) -> None:
        """
        Add a node to the graph.

        Args:
            node: The node to add.
        """
        self.nodes.add(node)

    def add_edge(self, from_node: T, to_node: T) -> None:
        """
        Add a directed edge from one node to another.

        Args:
            from_node: The source node.
            to_node: The target node that depends on the source.
        """
        self.add_node(from_node)
        self.add_node(to_node)
        self.graph[from_node].append(to_node)

    def topological_sort(self) -> List[T]:
        """
        Perform topological sort on the graph.

        Returns:
            A list of nodes in topological order.

        Raises:
            CircularDependencyError: If a cycle is detected in the graph.
        """
        # Initialize in-degree counts
        in_degree: Dict[T, int] = {node: 0 for node in self.nodes}

        # Calculate in-degrees
        for node in self.nodes:
            for neighbor in self.graph[node]:
                in_degree[neighbor] += 1

        # Queue nodes with no dependencies
        queue: deque[T] = deque()
        for node in self.nodes:
            if in_degree[node] == 0:
                queue.append(node)

        # Process the graph
        result: List[T] = []
        while queue:
            current = queue.popleft()
            result.append(current)

            for neighbor in self.graph[current]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        # Check for cycles
        if len(result) != len(self.nodes):
            # Find the cycle for better error reporting
            visited: Set[T] = set()
            path: List[T] = []

            def find_cycle(node: T) -> Optional[List[T]]:
                if node in path:
                    cycle_start = path.index(node)
                    return path[cycle_start:] + [node]

                if node in visited:
                    return None

                visited.add(node)
                path.append(node)

                for neighbor in self.graph[node]:
                    cycle = find_cycle(neighbor)
                    if cycle:
                        return cycle

                path.pop()
                return None

            for node in self.nodes:
                if node not in visited:
                    cycle = find_cycle(node)
                    if cycle:
                        # Handle cases where T might not be str
                        str_cycle = [str(n) for n in cycle]
                        raise CircularDependencyError(str_cycle)

            # Fallback if we can't identify the specific cycle
            remaining = self.nodes - set(result)
            str_remaining = [str(n) for n in remaining]
            raise CircularDependencyError(str_remaining)

        return result

    def reversed(self) -> "DependencyGraph[T]":
        """
        Create a new graph with all edges reversed.

        Useful for shutdown sequence where dependencies need to be torn down
        in reverse order of initialization.

        Returns:
            A new DependencyGraph with reversed edges.
        """
        reversed_graph = DependencyGraph[T]()

        # Add all nodes
        for node in self.nodes:
            reversed_graph.add_node(node)

        # Reverse all edges
        for from_node in self.nodes:
            for to_node in self.graph[from_node]:
                reversed_graph.add_edge(to_node, from_node)

        return reversed_graph


def get_attribute(obj: object, attr_path: str) -> object:
    """
    Get an attribute from an object using a dot-separated path.

    Args:
        obj: The object to get the attribute from.
        attr_path: Dot-separated path to the attribute (e.g., "config.debug").

    Returns:
        The attribute value.

    Raises:
        AttributeError: If any part of the path doesn't exist.
    """
    parts = attr_path.split(".")
    result = obj

    for part in parts:
        result = getattr(result, part)

    return result
