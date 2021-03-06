from network import *
from gene import *
from random import randint, choice

class Genome:

    def __init__(self, num_inputs, num_outputs, activation, init_network=True):
        self.species = 0
        self.fitness = 0
        if init_network:
            self.network = Network(num_inputs, num_outputs, activation)

    @staticmethod
    def create_from_network(network: Network):
        '''
            Create an instance of a genome from the given network
        '''
        genome = Genome(network.num_in, network.num_out, network.activation, init_network=False)
        genome.network = network
        return genome

    def are_same_species(self, other, configs=None) -> bool:
        ''' 
            Returns whether the genome belongs to the same species as the other one or not
        '''
        unmatched_genes = self.network.get_num_unmatched_node_genes(other.network)

        # diff -> average difference between two weights of the same connection present in both networks
        # n -> number of shared connection genes
        diff, n = 0, 0
        for conn_gene in self.network.conn_genes:
            for other_gene in other.network.conn_genes:
                if conn_gene.innov == other_gene.innov:
                    n += 1
                    diff += self.network.get_weight(conn_gene) - other.network.get_weight(other_gene)
        try:
            diff /= n
        except ZeroDivisionError:
            pass
        self_num_genes = len(self.network.conn_genes)+len(self.network.nodes)
        other_num_genes = len(other.network.conn_genes)+len(other.network.nodes)
        N = max(self_num_genes, other_num_genes)

        return configs['unmatched_genes_coeff']*unmatched_genes/N + configs['weight_diff_coeff']*diff < configs['compatibility_threshold']

    # TESTED
    def mutate_add_node(self, configs) -> tuple:
        '''
            Selects a random connection in the network between the nodes a->b, it disables it
            and it generates a new node c, then it forms the connections a->c and c->b.
        '''

        # If there are no connection there's no point in trying to form a node to substitute one,
        # it would just crash the whole program
        if len(self.network.conn_genes) == 0:
            return None
        
        conn_idx = np.random.randint(low=0, high=len(self.network.conn_genes)) # pick the connection in which to form the new node
        conn = self.network.conn_genes[conn_idx]
        self.network.disable_conn(conn_idx)
        self.network.gen_node()
        new_node_idx = self.network.node_genes[-1].index
        first_conn = ConnectionGene(conn.start, new_node_idx, 1)
        self.network.add_conn(first_conn, weight_var = configs['weight_init_std'])
        second_conn = ConnectionGene(new_node_idx, conn.end, 1)
        self.network.add_conn(second_conn, weight_var = configs['weight_init_std'])
        return ((first_conn.start, first_conn.end), (second_conn.start, second_conn.end))

    # TESTED
    def mutate_add_conn(self, configs, max_attemps=10) -> tuple:
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

        valid, attempts = False, 0
        while not valid and attempts < max_attemps:
            start_idx = randint(*start_valid_interval)
            end_idx = randint(*choice(end_valid_intervals)) 
            # cannot have a connection between a node and one with a lower index, done to avoid loops
            valid = not self.network.has_conn(start_idx, end_idx) and start_idx > end_idx
            attempts += 1  

        if not valid:
            return False, (-1,-1)

        conn_gene = ConnectionGene(start_idx, end_idx, 1)
        self.network.add_conn(conn_gene, weight_var = configs['weight_init_std'])
        return True, (start_idx, end_idx)

    # TESTED
    def mutate_change_weight(self, configs):
        ''' Changes one of the weights of the network randomly (according to a gaussian distribution) '''
        if len(self.network.conn_genes) == 0:
            return

        conn_idx = np.random.randint(low=0, high=len(self.network.conn_genes)) # pick a random connection to change
        self.network.set_weight(conn_idx, np.random.normal(scale=configs['weight_init_std']))

    # TESTED
    def mutate_change_threshold(self, configs):
        ''' Changes one of the thresholds of the nodes in the network randomly (according to a gaussian distribution) '''
        node_idx = np.random.randint(low=0, high=len(self.network.node_genes))
        self.network.node_genes[node_idx].bias = np.random.normal(scale=configs['threshold_init_std'])

    # TESTED
    def mutate_toggle_gene(self):
        ''' Toggles a random connection gene, meaning if it's enabled it gets disabled and viceversa '''
        if len(self.network.conn_genes) == 0:
            return

        conn_gene_idx = np.random.randint(low=0, high=len(self.network.conn_genes))
        if self.network.conn_genes[conn_gene_idx].enabled:
            self.network.disable_conn(conn_gene_idx)
        else:
            self.network.enable_conn(conn_gene_idx)

    def mutate(self, configs) -> tuple:
        '''
            Mutates the genome according to the given parameters \n
            configs -> a dictionary with all the following keys (going from 0 to 1):\n
                \tprob_add_node -> probability of adding a new node between a connection\n
                \tadd_conn_prob -> probability of adding a new connection between two nodes\n
                \tchange_weight_prob -> probability that every single weight in the network is changed randomly\n
                \tthreshold_change_prob -> probability that the threshold of a random neuron in the network is changed randomly\n
                \ttoggle_gene_prob -> probability that a gene is toggled (meaning it gets enabled or disabled)
        '''
        # list of the new connections formed during this mutation, each represented as a tuple as such:
        # (conn_start, conn_end, conn_idx), where conn_idx is the index of the connection in the network of this genome
        conns = []

        if np.random.uniform() <= configs['prob_add_node']:
            generated = self.mutate_add_node()
            if generated is not None:
                for conn in generated:
                    conns.append(conn)
        if np.random.uniform() <= configs['add_conn_prob']:
            res = self.mutate_add_conn(configs)
            if res[0]: # only keep track of it if a new connection was actually found
                conns.append(res[1])
        if np.random.uniform() <= configs['change_weight_prob']:
            self.mutate_change_weight(configs)
        if np.random.uniform() <= configs['threshold_change_prob']:
            self.mutate_change_threshold(configs)
        if np.random.uniform() <= configs['toggle_gene_prob']:
            self.mutate_toggle_gene()

        return conns


# TESTED
def crossover(first: Genome, second: Genome) -> Genome:
    ''' Returns the cross over between the genomes first and second '''
    conn_genes = [] 
    # maximum number of the index of a hidden node used in a connection, this is useful so only
    # the nodes used in a connection are added (or those necessary to make the connection matrix work)
    max_hidden_node_idx = -1

    fittest = first if first.fitness >= second.fitness else second

    f_min_conn_innov, f_max_conn_innov = first.network.get_weight_innov_interval()
    s_min_conn_innov, s_max_conn_innov = second.network.get_weight_innov_interval()

    # Since the loop works on the innovation numbers in an increasing order, 
    # they are already ordered when they are appended to conn_genes
    for conn_innov in range(min(f_min_conn_innov, s_min_conn_innov), max(f_max_conn_innov, s_max_conn_innov)+1):
        first_has_conn, second_has_conn = first.network.has_weight(conn_innov), second.network.has_weight(conn_innov)

        if first_has_conn and second_has_conn:
            # a matching gene is chosen randomly from the two parents
            base_network = first.network if np.random.uniform() <= 0.5 else second.network
            gene = base_network.get_conn_gene(conn_innov)
            conn_genes.append(gene)
            if gene.end > max_hidden_node_idx:
                max_hidden_node_idx = gene.end
        elif first_has_conn != second_has_conn: # one has to be true
            # an unmatching gene is always chosen from the fittest parent
            gene = fittest.network.get_conn_gene(conn_innov)
            if gene is not None:
                conn_genes.append(gene)
                if gene.end > max_hidden_node_idx:
                    max_hidden_node_idx = gene.end


    # GENERATE THE NODES (ONLY KEEP THE ONES USED IN THE CONNECTIONS)
    num_in, num_out = first.network.num_in, first.network.num_out
    node_genes = [NodeGene(i, NodeType.OUTPUT) for i in range(num_out)]+[NodeGene(num_out+i, NodeType.INPUT) for i in range(num_in)]
    node_genes += [NodeGene(len(node_genes)+i, NodeType.HIDDEN) for i in range(max_hidden_node_idx-len(node_genes)+1)]

    for node_idx in range(num_in+num_out, len(node_genes)):
        first_has_node, second_has_node = first.network.has_node(node_idx), second.network.has_node(node_idx)
        if first_has_node and second_has_node:
            base_network = first.network if np.random.uniform() <= 0.5 else second.network
            node_genes[node_idx].bias = base_network.node_genes[node_idx].bias
        elif first_has_node != second_has_node:
            try:
                node_genes[node_idx].bias = fittest.network.node_genes[node_idx].bias
            except IndexError:
                base_network = first.network if fittest == second.network else second.network
                node_genes[node_idx].bias = base_network.node_genes[node_idx].bias

    # for now I'll just assume both genomes use the same activation function
    net = Network(num_in, num_out, first.network.activation)
    net.load_structure(node_genes, conn_genes)

    genome = Genome.create_from_network(net)
    return genome