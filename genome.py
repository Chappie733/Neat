from math import e
from network import *
from gene import *
from random import randint, choice

class Genome:
    COMPATIBILITY_THRESHOLD = 3.0  
    UNMATCHED_GENES_COEFFICIENT = 0.5
    WEIGHTS_DIFFERENCE_COEFFICIENT = 0.5

    def __init__(self, num_inputs, num_outputs, activation):
        self.species = 0
        self.fitness = 0
        self.network = Network(num_inputs, num_outputs, activation)

    def are_same_species(self, other) -> bool:
        ''' 
            Returns whether the genome belongs to the same species
            as the other one or not
        '''
        unmatched_genes = self.network.get_num_unmatched_node_genes(other)+self.network.get_unmatched_conn_genes(other)

        # diff -> average difference between two weights of the same connection present in both networks
        # n -> number of shared connection genes
        diff, n = 0, 0
        for conn_gene in self.network.conn_genes:
            for other_gene in other.network.conn_genes:
                if conn_gene.innov == other_gene.innov:
                    n += 1
                    diff += self.network.get_weight(conn_gene) - other.network.get_weight(other_gene)
        diff /= n
        self_num_genes = len(self.network.conn_genes)+len(self.network.nodes)
        other_num_genes = len(other.network.conn_genes)+len(other.network.nodes)
        N = max(self_num_genes, other_num_genes)

        return self.UNMATCHED_GENES_COEFFICIENT*unmatched_genes/N + self.WEIGHTS_DIFFERENCE_COEFFICIENT*diff

    # TESTED
    def mutate_add_node(self) -> None:
        '''
            Selects a random connection in the network between the nodes a->b, it disables it
            and it generates a new node c, then it forms the connections a->c and c->b.
        '''

        # If there are no connection there's no point in trying to form a node to substitute one,
        # it would just crash the whole program
        if len(self.network.conn_genes) == 0:
            return
        
        conn_idx = np.random.randint(low=0, high=len(self.network.conn_genes)) # pick the connection in which to form the new node
        self.network.disable_conn(conn_idx)
        self.network.gen_node()
        new_node_idx = self.network.node_genes[-1].index
        self.network.add_conn(ConnectionGene(self.network.conn_genes[conn_idx].start, new_node_idx, 1))
        self.network.add_conn(ConnectionGene(new_node_idx, self.network.conn_genes[conn_idx].end, 1))

    # TESTED
    def mutate_add_conn(self, max_attemps=10) -> bool:
        '''
            Adds a new random connection gene in the genome (and thus in the network)\n
            max_attempts is the number of attempts made to generate a unique connection, meaning it
            determines the amount of times the function finds a new random connection, and discards it if
            it already exists.\n
            Returns whether the connection was formed (meaning the attempts were enough to randomly)
            form a valid connection gene
        '''
        # skip the output nodes, since a connection cannot stem from one of them
        start_valid_interval = (self.network.num_out, len(self.network.node_genes)-1)

        # the intervals in which the index of the ending node can be found, this excludes input nodes
        if self.network.node_genes[-1]._type == NodeType.HIDDEN:
            # since the randint() function is inclusive, if there are no hidden neurons the second interval
            # results in a weight stemming from the last (input) neuron
            end_valid_intervals = [(0, self.network.num_out-1), 
                                    (self.network.num_in+self.network.num_out, len(self.network.nodes)-1)]
        else:
            end_valid_intervals = [(0, self.network.num_out-1)]

        print(f"svi: {start_valid_interval}")
        print(f"evi: {end_valid_intervals}")

        valid, attempts = False, 0
        while not valid and attempts < max_attemps:
            start_idx = randint(*start_valid_interval)
            end_idx = randint(*choice(end_valid_intervals)) 
            # cannot have a connection between a node and one with a lower index, done to avoid loops
            valid = not self.network.has_conn(start_idx, end_idx) and start_idx > end_idx
            attempts += 1  

        if not valid:
            return False

        conn_gene = ConnectionGene(start_idx, end_idx, 1)
        self.network.add_conn(conn_gene)
        return True

    # TESTED
    def mutate_change_weight(self):
        ''' Changes one of the weights of the network randomly (according to a gaussian distribution) '''
        conn_idx = np.random.randint(low=0, high=len(self.network.conn_genes)) # pick a random connection to change
        self.network.set_weight(conn_idx, np.random.normal(scale=1))

    
    def mutate_change_threshold(self):
        ''' Changes on the thresholds of the nodes in the network randomly (according to a gaussian distribution) '''
        node_idx = np.random.randint(low=0, high=len(self.network.node_genes))
        self.network.node_genes[node_idx].bias = np.random.normal(scale=1)

    def mutate(self, node_add_prob=0.3, conn_add_prob=0.3, weight_change_prob=0.6, gene_toggle_prob=0.1):
        '''
            Mutates the genome according to the given parameters
            node_add_prob -> probability of adding a new node between a connection\n
            conn_add_prob -> probability of adding a new connection between two nodes\n
            weight_change_prob -> probability that every single weight in the network is changed randomly\n
            gene_toggle_prob -> probability that a gene is toggled (meaning it gets enabled or disabled)
        '''
        if np.random.uniform() <= node_add_prob:
            self.mutate_add_node()
        if np.random.uniform() <= conn_add_prob:
            self.mutate_add_conn()
        if np.random.uniform() <= weight_change_prob:
            self.mutate_change_weight()