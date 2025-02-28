import random
import string
import subprocess
import sys
import signal

sys.setrecursionlimit(10000) 

def is_nt(v):
    return len(v) > 2 and (v[0], v[-1]) == ('<', '>')

def tree_to_str(tree):
    symbol, children, *_ = tree
    if children:
        return ''.join(tree_to_str(c) for c in children)
    else:
        return '' if is_nt(symbol) else symbol
    
# From Mimid; not used by STALAGMITE.
ASCII_MAP = {
        '[__WHITESPACE__]': string.whitespace,
        '[__DIGIT__]': string.digits,
        '[__ASCII_LOWER__]': string.ascii_lowercase,
        '[__ASCII_UPPER__]': string.ascii_uppercase,
        '[__ASCII_PUNCT__]': string.punctuation,
        '[__ASCII_LETTER__]': string.ascii_letters,
        '[__ASCII_ALPHANUM__]': string.ascii_letters + string.digits,
        '[__ASCII_PRINTABLE__]': string.printable
        }

class Fuzzer:
    def __init__(self, grammar):
        self.grammar = grammar

    def fuzz(self, key='<start>'):
        raise NotImplemented()

FUZZRANGE = 10

class LimitFuzzer(Fuzzer):
    def symbol_cost(self, grammar, symbol, seen):
        if symbol in self.key_cost: return self.key_cost[symbol]
        if symbol in seen:
            self.key_cost[symbol] = float('inf')
            return float('inf')
        v = min((self.expansion_cost(grammar, rule, seen | {symbol})
                    for rule in grammar.get(symbol, [])), default=0)
        self.key_cost[symbol] = v
        return v

    def expansion_cost(self, grammar, tokens, seen):
        return max((self.symbol_cost(grammar, token, seen)
                    for token in tokens if token in grammar), default=0) + 1

    def nonterminals(self, rule):
        return [t for t in rule if is_nt(t)]

    def iter_gen_key(self, key, max_depth, first_choice = None):
        def get_def(t):
            if t in ASCII_MAP:
                return [random.choice(ASCII_MAP[t]), []]
            elif t and t[-1] == '+' and t[0:-1] in ASCII_MAP:
                num = random.randrange(FUZZRANGE) + 1
                val = [random.choice(ASCII_MAP[t[0:-1]]) for i in range(num)]
                return [''.join(val), []]
            elif is_nt(t):
                return [t, None]
            else:
                return [t, []]

        root = [key, None]
        queue = [(0, root)]
        while queue:
            # get one item to expand from the queue
            (depth, item), *queue = queue
            key = item[0]
            if item[1] is not None: continue
            grammar = self.grammar if depth < max_depth else self.cheap_grammar
            if first_choice is not None:
                chosen_rule = grammar[key][first_choice]
                first_choice = None
            else:
                chosen_rule = random.choice(grammar[key])
            expansion = [get_def(t) for t in chosen_rule]
            item[1] = expansion
            for t in expansion: queue.append((depth+1, t))
            #print("Fuzz: %s" % key, len(queue), file=sys.stderr)
        #print(file=sys.stderr)
        return root

    def gen_key(self, key, depth, max_depth):
        if key in ASCII_MAP:
            return (random.choice(ASCII_MAP[key]), [])
        if key and key[-1] == '+' and key[0:-1] in ASCII_MAP:
            m = random.randrange(FUZZRANGE) + 1
            return (''.join([random.choice(ASCII_MAP[key[0:-1]]) for i in range(m)]), [])
        if key not in self.grammar: return (key, [])
        if depth > max_depth:
            #return self.gen_key_cheap_iter(key)
            clst = sorted([(self.cost[key][str(rule)], rule) for rule in self.grammar[key]])
            rules = [r for c,r in clst if c == clst[0][0]]
        else:
            rules = self.grammar[key]
        return (key, self.gen_rule(random.choice(rules), depth+1, max_depth))

    def gen_rule(self, rule, depth, max_depth):
        return [self.gen_key(token, depth, max_depth) for token in rule]

    def fuzz(self, key='<start>', max_depth=10, first_choice = None):
        tree = self.iter_gen_key(key=key, max_depth=max_depth, first_choice=first_choice)
        inp = tree_to_str(tree)
        return inp, tree

    def __init__(self, grammar):
        super().__init__(grammar)
        self.key_cost = {}
        self.cost = self.compute_cost(grammar)
        self.cheap_grammar = {}
        for k in self.cost:
            rules = self.grammar[k]
            min_cost = min([self.cost[k][str(r)] for r in rules])
            self.cheap_grammar[k] = [r for r in self.grammar[k] if self.cost[k][str(r)] == min_cost]

    def compute_cost(self, grammar):
        cost = {}
        for k in grammar:
            cost[k] = {}
            for rule in grammar[k]:
                cost[k][str(rule)] = self.expansion_cost(grammar, rule, set())
            if len(grammar[k]):
                assert len([v for v in cost[k] if v != float('inf')]) > 0
        return cost
    
        
def put_can_parse(put, inp):
    p = subprocess.Popen(put, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = p.communicate(input=inp.encode('latin-1')) # Encoding handles 0xff (EOI) correctly

    if p.returncode == 0:
        return True
    else:
        if p.returncode in [-signal.SIGILL, -signal.SIGABRT, -signal.SIGFPE, -signal.SIGTRAP, -signal.SIGSEGV]:
            # In case the process core dumped, e.g. because of div-by-zero [->SIGFPE] (calc), we cannot make a statement about the syntax.
            return None
        else:
            return False