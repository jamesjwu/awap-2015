import networkx as nx
import random
from base_player import BasePlayer
from settings import *
from collections import deque, defaultdict
import game

RANK_MULTIPLIER = .5
STOP_BUILDING_THRESHOLD = 800
STATION_RANGE_MULTIPLIER = 0.5
DISTANCE_FACTOR = 40

class Player(BasePlayer):

    """
    You will implement this class for the competition. DO NOT change the class
    name or the base class.
    """

    # You can set up static state here
    station_costs = dict()
    stations = [] # list of graph nodes
    neighbor_map = dict()
    rank_map = defaultdict(int)

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

        self.station_range = max(1, int(nx.radius(state.graph) * STATION_RANGE_MULTIPLIER))
        global RANK_THRESHOLD
        RANK_THRESHOLD = max(1, RANK_MULTIPLIER * int(nx.radius(state.graph)))

        for node in state.graph.nodes():
            self.neighbor_map[node] = dict()
            queue = deque([(node, 0)])
            visited = set()
            while queue:
                n, depth = queue.popleft()
                visited.add(n)
                if depth in self.neighbor_map[node]:
                    self.neighbor_map[node][depth].update(set([n]))
                else:
                    self.neighbor_map[node][depth] = set([n])
                if depth < self.station_range:
                    neighbors = state.graph.neighbors(n)
                    filtered_neighbors = [n for n in neighbors if n not in visited]
                    queue.extend([(n, depth + 1) for n in filtered_neighbors])
                    visited.update(filtered_neighbors)

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
        return order.get_money() - distance * DECAY_FACTOR

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


    def is_fulfilled(self, order, distance):
        if distance == 0: return True
        return DISTANCE_FACTOR/distance + self.order_value(order, distance) > 10

    def determine_stations(self, orders, commands, update_rank=True):
        graph = self.state.get_graph()
        fulfilled_orders = set()

        for (order, val) in orders:
            queue = deque([(order.node, [])])
            visited = set()
            discovery_map = dict()
            order_fulfilled = False
            while queue:
                node, path = queue.popleft()

                if update_rank and len(path) < RANK_THRESHOLD:
                    self.rank_map[node] += RANK_THRESHOLD - len(path)

                if node in self.stations:
                    curr_node = node
                    path.append(node)
                    order_fulfilled = True
                    if self.is_fulfilled(order, len(path)-1):
                        fulfilled_orders.add(order)
                        commands.append(self.send_command(order, path[::-1]))
                        self.mark_as_used(path, graph)
                    break

                visited.add(node)
                path.append(node)
                neighbors = graph.neighbors(node)
                filtered_neighbors = [(n, path[:]) for n in neighbors if n not in visited and not graph.edge[node][n]['in_use']]
                queue.extend(filtered_neighbors)


        unfulfilled = deque([(o, v) for (o, v) in orders if o not in fulfilled_orders])
        return unfulfilled

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

        # Step 2: find paths for orders, return unfulfilled orders
        commands = []
        unfulfilled = self.determine_stations(order_heuristics, commands)
        # Step 3: add new stations if worth
        if GAME_LENGTH - self.state.time >= STOP_BUILDING_THRESHOLD:
            n = self.state.graph.number_of_nodes()
            while len(self.stations) < n and unfulfilled:
                (order, heuristic) = unfulfilled.popleft()

                # If we have no money, stop trying to build
                cost = self.new_station_cost()
                if self.state.money < cost:
                    break

                new_station = self.find_happy_station(order, heuristic)
                if new_station is not None:
                    commands.append(self.build_command(new_station))
                    self.state.money -= self.new_station_cost()
                    self.stations.append(new_station)
                    # Rerun step 2 (find more paths to unfulfilled with new station)
                    unfulfilled = self.determine_stations(orders=unfulfilled, commands=commands, update_rank=False)

        return commands

    def new_station_cost(self):
        """ Cost of building a new station """
        return self.station_costs[len(self.stations)]

    def find_happy_station(self, order, heuristic):
        """
        Compute the optimal location for adding a new station near
        an unfulfilled station.
        """
        # Get all neighbors within self.station_range depth away from order node
        neighbors = reduce(lambda x,y: x | y,
                           [self.neighbor_map[order.node][d] for d in xrange(self.station_range)])
        # If there is already a station within range, don't build another
        if any([s in neighbors for s in self.stations]):
            return None

        best_neighbor = max(neighbors, key=lambda v: self.rank_map[v])

        return best_neighbor
