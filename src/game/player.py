import networkx as nx
import random
from base_player import BasePlayer
from settings import *
from collections import deque


HAPPY_THRESHOLD = 20

class Player(BasePlayer):

    """
    You will implement this class for the competition. DO NOT change the class
    name or the base class.
    """

    # You can set up static state here
    station_costs = dict()
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

        # Precompute cost of the i^th station as map
        self.station_costs = dict([
            (i, INIT_BUILD_COST * (BUILD_FACTOR ** i)) for i in xrange(state.graph.number_of_nodes())
        ])

        return

    # Checks if we can use a given path
    def path_is_valid(self, state, path):
        graph = state.get_graph()
        for i in range(0, len(path) - 1):
            if graph.edge[path[i]][path[i + 1]]['in_use']:
                return False
        return True

    def order_value(self, order, distance):
        """
        Calculates the value of an order
        """
        # Currently returns the value of the order minus the distance
        return order.get_money() - distance

    def compute_heuristic(self):
        """
        Runs multisource BFS to calculate the heuristic of orders
        """
        if not self.stations:
            all_orders = sorted(self.state.get_pending_orders(), key=lambda x: -x.get_money())
            return [(i, self.order_value(i, 0)) for i in all_orders]

        graph = self.state.get_graph()
        visited = set((s, 0) for s in self.stations)

        visiting = deque((s, 0) for s in self.stations)

        results = []

        # get all order nodes

        orders = dict((i.node, i) for i in self.state.get_pending_orders())

        while visiting:
            curr, distance = visiting.popleft()
            if curr in orders:
                #print curr, " is an order "
                results.append((orders[curr], self.order_value(orders[curr], distance)))

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
        self.state = state
        graph = state.get_graph()
        commands = []

        #if not self.has_built_station:
        #    commands.append(self.build_command(station))
        #    self.stations.append(station)
        #    self.has_built_station = True

        #pending_orders = state.get_pending_orders()
        #if len(pending_orders) != 0:
        #    order = random.choice(pending_orders)
        #    path = nx.shortest_path(graph, station, order.get_node())
        #    if self.path_is_valid(state, path):
        #        commands.append(self.send_command(order, path))

        # Step 1: compute order heuristics
        order_heuristics = self.compute_heuristic()
        if (self.state.time < 1):
            print order_heuristics

        # Step 3: add new stations if worth
        if len(order_heuristics) > 0 and len(self.stations) < self.state.graph.number_of_nodes():
            for (order, heuristic) in order_heuristics:
                #print "order:", order, "heuristic:", heuristic
                if self.happy(order, heuristic) > HAPPY_THRESHOLD:
                    print "building a station at", order.node
                    commands.append(self.build_command(order.node))
                    self.state.money -= self.new_station_cost()
                    self.stations.append(order.node)

                    # for now since we're building on top of orders, just fulfill it immediately
                    commands.append(self.send_command(order, [order.node]))

        # Step 4: should probably rerun step 2 (send more commands using new station)

        return commands

    def new_station_cost(self):
        """ Cost of building a new station """
        return self.station_costs[len(self.stations)]

    def happy(self, order, heuristic):
        """
        Compute the happiness we gain from building a new station at an
        order location. -1 if we can't build
        """
        cost = self.new_station_cost()
        can_build = self.state.money >= cost
        happiness = self.state.money - cost + order.money
        #print "HAPPINESS:", happiness
        return happiness if can_build else -1
