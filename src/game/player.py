import networkx as nx
import random
from base_player import BasePlayer
from settings import *
from collections import deque, defaultdict

HAPPY_THRESHOLD = 20
RANK_THRESHOLD = 3

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

        self.rank_map = defaultdict(int)

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

    def mark_as_used(self, path, graph):
        for i in xrange(0, len(path)-1):
            graph[path[i]][path[i+1]]['in_use'] = True

    def determine_stations(self, orders):
        graph = self.state.get_graph()
        order_commands = []
        fulfilled_orders = []
        print orders
        for (order, val) in orders:
            queue = deque([(order.node, [])])
            visited = set()
            discovery_map = dict()
            order_fulfilled = False
            while queue:
                node, path = queue.popleft()
                if len(path) < RANK_THRESHOLD:
                    self.rank_map[node] += RANK_THRESHOLD - len(path)

                if node in self.stations:
                    curr_node = node
                    path.append(node)
                    order_fulfilled = True
                    break
                visited.add(node)
                path.append(node)
                neighbors = graph.neighbors(node)
                filtered_neighbors = [(n, path[:]) for n in neighbors if n not in visited and not graph.edge[node][n]['in_use']]
                queue.extend(filtered_neighbors)


            if order_fulfilled:
                fulfilled_orders.insert(0, order)
                order_commands.append(self.send_command(order, path[::-1]))
                self.mark_as_used(path, graph)

        unfulfilled = [(o, v) for (o, v) in orders if o not in fulfilled_orders]
        return order_commands, unfulfilled

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

        # Step 1: compute order heuristics
        order_heuristics = self.compute_heuristic()
        if (self.state.time < 1):
            print order_heuristics

        # Step 2: find paths for orders, return unfulfilled orders
        commands, unfulfilled = self.determine_stations(order_heuristics)

        # Step 3: add new stations if worth
        if len(unfulfilled) > 0 and len(self.stations) < self.state.graph.number_of_nodes():
            for (order, heuristic) in unfulfilled:
                print "order:", order, "heuristic:", heuristic
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
