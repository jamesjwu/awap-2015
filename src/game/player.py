import networkx as nx
import random
from base_player import BasePlayer
from settings import *
from collections import deque


class Player(BasePlayer):

    """
    You will implement this class for the competition. DO NOT change the class
    name or the base class.
    """

    # You can set up static state here
    has_built_station = False
    # List of graph.nodes
    stations = []

    def __init__(self, state):
        """
        Initializes your Player. You can set up persistent state, do analysis
        on the input graph, engage in whatever pre-computation you need. This
        function must take less than Settings.INIT_TIMEOUT seconds.
        --- Parameters ---
        state : State
            The initial state of the game. See state.py for more information.
        """

        return

    # Checks if we can use a given path
    def path_is_valid(self, state, path):
        graph = state.get_graph()
        for i in range(0, len(path) - 1):
            if graph.edge[path[i]][path[i + 1]]['in_use']:
                return False
        return True

    def value(self, order, distance):
        """
        Calculates the value of an order
        """
        # Currently returns the value of the order minus the distance
        return order.get_money() - distance

    def compute_heuristic(self):
        """
        Runs multisource BFS to calculate the heuristic of orders
        """
        graph = self.state.get_graph()
        visited = set((s, 0) for s in self.stations)

        visiting = deque((s, 0) for s in self.stations)

        results = []

        # get all order nodes

        orders = dict((i.node, i) for i in self.state.get_pending_orders())

        while visiting:
            curr, distance = visiting.popleft()
            if curr in orders:
                print curr, " is an order "
                results.append((orders[curr], self.value(orders[curr], distance)))

            for neighbor in graph.neighbors(curr):
                # If we aren't using this edge
                if (not graph.edge[curr][neighbor]['in_use']) and neighbor not in visited:
                    visiting.append((neighbor, distance+1))
                    # if the neighbor is an order, add it to results
                    visited.add(neighbor)

        return sorted(results, key=lambda x: -x[1])

    def step(self, state):
        """
        Determine actions based on the current state of the city. Called every
        time step. This function must take less than Settings.STEP_TIMEOUT
        seconds.
        --- Parameters ---
        state : State
            The state of the game. See state.py for more information.
        --- Returns ---
        commands : dict list
            Each command should be generated via self.send_command or
            self.build_command. The commands are evaluated in order.
        """

        # We have implemented a naive bot for you that builds a single station
        # and tries to find the shortest path from it to first pending order.
        # We recommend making it a bit smarter ;-)
        self.state = state
        graph = state.get_graph()
        station = graph.nodes()[0]

        commands = []
        if not self.has_built_station:
            commands.append(self.build_command(station))
            self.stations.append(station)
            self.has_built_station = True

        print "HEURISTIC:" + str(self.compute_heuristic())

        pending_orders = state.get_pending_orders()
        if len(pending_orders) != 0:
            order = random.choice(pending_orders)
            path = nx.shortest_path(graph, station, order.get_node())
            if self.path_is_valid(state, path):
                commands.append(self.send_command(order, path))

        return commands
