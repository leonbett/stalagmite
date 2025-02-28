import sys
import os
import json
import argparse
import re
import ast

from pprint import pprint

from fuzzingbook.GrammarFuzzer import display_tree

from generalize_tidy import inline_single_rules_and_opt_generalization
from generalize_helpers import unreachable_nonterminals, load_json_file, serialize_grammar
from generalize_tokens import generalize_tokens

from longest_inc_subseq import longest_increasing_subsequence

CTX_NONE = 0
CTX_COARSE = 1
CTX_FINE = 2
CTX_WINDOW = 3
WINDOW_SIZE = 5

count_traces = 0
count_fixed_traces = 0
count_fixed_positions = 0 

def prune_external(executioncontext):
    last_frame = executioncontext[-1]
    callee = last_frame["callee"]
    if callee.startswith('__external_') and \
        '_L_0x' not in callee:
        return executioncontext[:-1]
    return executioncontext

def order_trace(j: dict, all_scc):
    orig = {} # Trace with last reads only (for debugging)
    oj = {} # Ordered trace

    # For statistics:
    fix_inp_pos_prev = set()
    fix_inp_pos_bt = set()

    # Note: All data structures != {oj,j,orig} use an *int* key.
    order_to_inp_pos = {}
    order_to_call_stack = {}
    inp_pos_to_orders = {}

    for inp_pos in sorted([int(k) for k in j.keys()]):
        read_orders = j[str(inp_pos)]["readorders"] # plural
        execution_contexts = j[str(inp_pos)]["executioncontexts"]
        solutions = j[str(inp_pos)]["solutions"]

        orig[str(inp_pos)] = {
            "readorder": read_orders[-1], # singular
            "executioncontext": execution_contexts[-1],
            "solutions": solutions
        }

        for i, order in enumerate(read_orders):
            order_to_inp_pos[order] = inp_pos
            order_to_call_stack[order] = execution_contexts[i]

        inp_pos_to_orders[inp_pos] = read_orders
    
    missing_positions = set()
    lis = [] # Longest Increasing Subsequence
    while True:
        orders = []
        for inp_pos in range(len(j)):
            if inp_pos not in inp_pos_to_orders:
                missing_positions.add(inp_pos)
            if inp_pos not in inp_pos_to_orders or \
                inp_pos_to_orders[inp_pos] == []:
                # This is not a re-read, we cannot "backtrack" to get a complete LIS
                # Hence, we now have to set context of inp_pos to context of inp_pos-1.
                assert inp_pos!=0
                prev_orders = inp_pos_to_orders[inp_pos-1]
                fake_orders = [prev_orders[-1] + 0.1] # this is now in order by construction
                inp_pos_to_orders[inp_pos] = fake_orders
                order_to_inp_pos[fake_orders[-1]] = inp_pos
                order_to_call_stack[fake_orders[-1]] = order_to_call_stack[prev_orders[-1]]
                fix_inp_pos_prev.add(inp_pos)
            orders.append(inp_pos_to_orders[inp_pos][-1])

        lis = longest_increasing_subsequence(orders)
        print("lis: ", lis)
        if len(lis) == len(j):
            # done
            break
        else:
            odd = sorted(list(set(orders) - set(lis))) # "orders" which are not in lis
            assert len(odd) > 0
            inp_pos_to_orders[order_to_inp_pos[odd[0]]].pop()
            fix_inp_pos_bt.add(order_to_inp_pos[odd[0]])
    
    print("order_trace -- fixed inp indices (set to predecessor ctx [i-1]): ", fix_inp_pos_prev)
    print("order_trace -- fixed inp indices (set to previous read [pop]): ", fix_inp_pos_bt)

    global count_fixed_traces, count_fixed_positions
    if fix_inp_pos_bt or fix_inp_pos_prev:
        count_fixed_traces += 1
    count_fixed_positions += len(fix_inp_pos_prev.union(fix_inp_pos_bt))

    print("final orders: ", lis)

    for i, order in enumerate(lis):
        key = str(i)
        if i in fix_inp_pos_bt or i in fix_inp_pos_prev:
            orig_execution_context = order_to_call_stack[order]
            pruned_execution_context = prune_external(orig_execution_context)
            execution_context = pruned_execution_context
            print("Pruned call stack of input position ", i)
            print("From: ", orig_execution_context)
            print("To:   ", pruned_execution_context)
            print("Change?: ", orig_execution_context != pruned_execution_context)
        else:
            execution_context = order_to_call_stack[order]

        if all_scc:
            assert False, "Not implemented"

        if i in missing_positions:
            solutions = [a for a in range(1, 256)]
        else:
            solutions = j[key]["solutions"]
        oj[key] = {
            "readorder": order,
            "executioncontext": execution_context,
            "solutions": solutions
        }
    
    assert len(oj) == len(j), "max lis does not include all input positions!"
    return oj, orig


OUTPUT_ORDERED_TRACES = False

class ExecutionTrace:
    def __init__(self, j: dict, all_scc: list, trace_fname):
        print("Processing: ", trace_fname)
        global count_traces
        count_traces += 1
        self.d_inp_pos_to_trace = {}
        self.trace_fname = trace_fname
        self.all_scc = all_scc
        ordered_trace, orig = order_trace(j, all_scc)
        if OUTPUT_ORDERED_TRACES: # for debugging
            file_name = os.path.basename(trace_fname)
            with open(f"traces_ordered/{file_name}", "w") as f:
                json.dump(ordered_trace, f, indent=1)
            with open(f"traces_last_read/{file_name}", "w") as f:
                json.dump(orig, f, indent=1)
        self.ordered_trace = ordered_trace

    def get(self):
        return self.ordered_trace
    

re_loop_node = re.compile(r'<(.+)@(\d+)_L(\d+)>')
def is_loop(s):
    return re.match(re_loop_node, s) != None

re_iteration_node = re.compile(r'<(.+)@(\d)+_L(\d+):I(\d+)>')
def is_iteration(s):
    return re.match(re_iteration_node, s) != None

def get_iteration(s):
    m = re.match(re_iteration_node, s)
    assert m
    return int(m.group(4))

# => Assumption: Every call is unique (json_parse_value@1 etc.).
# We do this with caller instructions as context, simplified with d_simplify_ctx.
class ExecutionTree:
    def __init__(self, g, isTokenCursor, token_grammar: dict, ctx_mode, d_terminals, ctr_terminals, d_simplify_ctx, d_ctr_simplify_ctx, d_simple_loops):
        self.tree = [] #("<start>", [])
        self.g = g
        self.isTokenCursor = isTokenCursor
        self.token_grammar = token_grammar
        self.ctx_mode = ctx_mode
        self.execution_trace = None

        self.d_terminals = d_terminals #{}
        self.ctr_terminals = ctr_terminals#0

        self.d_simplify_ctx: dict = d_simplify_ctx # maps (f, 0x123) => 1...
        self.d_ctr_simplify_ctx: dict = d_ctr_simplify_ctx # maps f => 1,2,3..
        
        self.d_simple_loops: dict = d_simple_loops

    def add_trace(self, et: ExecutionTrace):
        trace = et.get()
        assert self.execution_trace is None
        self.execution_trace = et
        inp_pos: str
        for i, inp_pos in enumerate(sorted(trace.keys(), key=lambda x: int(x))):
            order = trace[inp_pos]["readorder"]
            execution_context: dict = trace[inp_pos]["executioncontext"]
            solutions: list = trace[inp_pos]["solutions"]
            if i == len(trace.keys()) - 1 and solutions == [0]:
                # Remove trailing 0x00
                solutions = []
            call_stack = []
            ctxs = [] # only using call_ctx; this implies f in our case.
            for frame in execution_context:
                callsite = frame["callsite"]
                callee = frame["callee"]
                loopiterations = frame["loopiterations"]
                ctxs.append(callsite)

                # These ctx_mode granularity is about merging traces.
                # CTX_NONE => Merge all traces based on current function only.
                # CTX_COARSE => Merge all traces based on current function and caller.
                # CTX_FINE => Merge all traces based on entire call path.
                # CTX_WINDOW => Merge all traces based on a window of k frames.

                if self.ctx_mode == CTX_NONE:
                    joined_ctx = ""
                elif self.ctx_mode == CTX_COARSE:
                    joined_ctx = ctxs[-1]
                elif self.ctx_mode == CTX_FINE:
                    joined_ctx = ",".join(ctxs)
                elif self.ctx_mode == CTX_WINDOW:
                    joined_ctx = ",".join(ctxs[len(ctxs)-WINDOW_SIZE:])
                else:
                    assert False, "not implemented"

                # Convert loop_iterations to string for visualization
                if callee not in self.d_ctr_simplify_ctx:
                    self.d_ctr_simplify_ctx[callee] = 0
                if (callee, joined_ctx) not in self.d_simplify_ctx:
                    self.d_simplify_ctx[(callee, joined_ctx)] = self.d_ctr_simplify_ctx[callee]
                    self.d_ctr_simplify_ctx[callee] += 1

                call_stack.append(f"{callee}@{self.d_simplify_ctx[(callee, joined_ctx)]}")

                if loopiterations != []:
                    for loopiteration in loopiterations:
                        loopheader: str = loopiteration["loopheader"]
                        iterationcount: int = loopiteration["iterationcount"]

                        if callee not in self.d_simple_loops:
                            self.d_simple_loops[callee] = {}
                        if loopheader not in self.d_simple_loops[callee]:
                            if len(self.d_simple_loops[callee]) == 0:
                                self.d_simple_loops[callee][loopheader] = 0
                            else:
                                self.d_simple_loops[callee][loopheader] = max(self.d_simple_loops[callee].values()) + 1

                        simple_loop_id = self.d_simple_loops[callee][loopheader]
                        call_stack.append(f"{callee}@{self.d_simplify_ctx[(callee, joined_ctx)]}_L{simple_loop_id}") # loop
                        call_stack.append(f"{callee}@{self.d_simplify_ctx[(callee, joined_ctx)]}_L{simple_loop_id}:I{iterationcount}") # loop iter

            print("inserting call_stack: ", call_stack)
            self.insert_path(self.tree, call_stack, solutions)
        self.tree = self.tree[0] if self.tree else ()

    def insert_path(self, tree, path, solutions):
        if not path:
            if not self.isTokenCursor:
                DELETE_NULL = True
                if DELETE_NULL: solutions = [s for s in solutions if s != 0]
            solutions_str = str(sorted(solutions))
            if solutions_str not in self.d_terminals:
                self.ctr_terminals += 1
                self.d_terminals[solutions_str] = self.ctr_terminals
            subtree = (f"<__T{self.d_terminals[solutions_str]}>", [(solutions_str, [])]) # string repr of list of possible terminals as leaf
            tree.append(subtree)
            return tree

        node, *rest = path
        node = f"<{node}>"

        # Only insert at rightmost place, if possible; otherwise generate a new subtree.
        if len(tree) > 0:
            n, children = tree[-1]
            if n == node:
                tree[-1] = (n, self.insert_path(children, rest, solutions))
                return tree
            
        subtree = self.insert_path([], rest, solutions)
        tree.append((node, subtree))
        return tree
    
    def handle_solutions(self, node, children):
        solutions = ast.literal_eval(children[0][0])
        if solutions == []:
            if [] not in self.g[node]:
                self.g[node].append([]) # epsilon
        else:
            if self.isTokenCursor:
                # This means the token in unconstrained; 256 is the limit of MiningExecutor::solveToken.
                if len(solutions) >= 255:
                    for nt in self.token_grammar:
                        if nt.startswith("<TOK_"):
                            rule = [nt]
                            if rule not in self.g[node]:
                                self.g[node].append(rule)
                else:
                    for sol in solutions:
                        token = f"<TOK_{sol}>"
                        assert token in self.token_grammar, f"Error: Token {token} not found in the token grammar."
                        rule = [token]
                        if rule not in self.g[node]:
                            self.g[node].append(rule)
            else:
                for sol in solutions:
                    rule = [chr(sol)]
                    if rule not in self.g[node]:
                        self.g[node].append(rule)

    def handle_loops(self, node, children):
        iteration_cnt = len(children)
        continue_nt = node[:-1] + "_cont>"
        exit_nt = node[:-1] + "_exit>"

        self.g[node] = [[continue_nt, node], [exit_nt]]
        for n in [continue_nt, exit_nt]:
            if n not in self.g:
                self.g[n] = []

        for i, c in enumerate(children):
            node_, children_ = c
            assert is_iteration(node_)

            rule = [c_[0] for c_ in children_]
            if i == iteration_cnt - 1:
                if rule not in self.g[exit_nt]:
                    self.g[exit_nt].append(rule)
            else:
                if rule not in self.g[continue_nt]:
                    self.g[continue_nt].append(rule)

    def handle_general_node(self, node, children):
        rule = [c[0] for c in children]
        if rule not in self.g[node]:
            self.g[node].append(rule)

    def to_grammar(self):
        node, children = self.tree
        if "<start>" in self.g:
            assert self.g["<start>"] == [[node]], "start symbol must match across traces"
        else:
            self.g["<start>"] = [[node]]
        q = [(node, children)]
        while q:
            node, children = q.pop(0)
            if children:
                if node not in self.g:
                    self.g[node] = []
                if node.startswith("<__T"): # Leaf node with concrete solutions
                    if not self.isTokenCursor: assert len(children) == 1
                    if self.isTokenCursor: assert len(children) > 0
                    self.handle_solutions(node, children)
                elif is_loop(node):
                    self.handle_loops(node, children)
                else:
                    self.handle_general_node(node, children)
                q.extend(children)
        return self.g

    def get(self):
        return self.tree

class ExecutionForest:
    def __init__(self, directory, isTokenCursor: bool, token_grammar: dict, ctx_mode: int, all_scc: list, simplify: bool):
        self.g = {}
        self.isTokenCursor = isTokenCursor
        self.token_grammar = token_grammar
        self.d_terminals = {}
        self.ctr_terminals = 0
        self.d_simplify_ctx = {}
        self.d_ctr_simplify_ctx = {}
        self.d_simple_loops = {}
        self.directory = directory
        self.ctx_mode = ctx_mode
        self.all_scc = all_scc

        tracefiles = [os.path.join(directory, f) for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))]
        for tracefile in tracefiles:
            print("Loading ", tracefile)
            j = load_json_file(tracefile)
            exec_trace = ExecutionTrace(j, self.all_scc, tracefile)
            exec_tree = ExecutionTree(self.g, self.isTokenCursor, self.token_grammar, self.ctx_mode, self.d_terminals, self.ctr_terminals, self.d_simplify_ctx, self.d_ctr_simplify_ctx, self.d_simple_loops)
            exec_tree.add_trace(exec_trace)
            self.g = exec_tree.to_grammar() # Accumulated across ExecutionTrees
            self.ctr_terminals = exec_tree.ctr_terminals # passed by value (unlike the dicts), so we need to save it

        serialize_grammar(self.g, "intermediate_grammar.json")

        # Post-process the grammar
        self.fix_loops()
        self.generalize_tokens()
        if simplify: self.simplify_grammar()
        for nt in unreachable_nonterminals(self.g, start_symbol="<start>"):
            del self.g[nt]
    
    def fix_loops(self):
        g_copy = {**self.g}
        for nt in g_copy:
            if is_loop(nt):
                rule_set = self.g[nt]
                cont_rule = rule_set[0] # [continue_nt, node]
                exit_rule = rule_set[1] # [exit_nt]
                cont_nt = cont_rule[0]
                if self.g[cont_nt] == []:
                    print(f"WARN: no continue iterations in {cont_nt}. Will delete this NT. Hence the loop only has an exit iteration now.")
                    del self.g[cont_nt]
                    self.g[nt] = [exit_rule]

        serialize_grammar(self.g, "loopfix_grammar.json")

    def generalize_tokens(self):
        if self.isTokenCursor:
            self.g = {**self.g, **self.token_grammar}
        else:
            self.g = generalize_tokens(self.g)

        serialize_grammar(self.g, "nonsimplified_grammar.json")
    
    def simplify_grammar(self):
        print("Doing inline and opt generalization")
        self.g = inline_single_rules_and_opt_generalization(self.g)

    def get_grammar(self):
        return self.g

def main():
    parser = argparse.ArgumentParser(description='Argument Parser')
    group_mode = parser.add_mutually_exclusive_group(required=True)
    group_mode.add_argument('--single', action='store_true', help='Mine grammar from one trace')
    group_mode.add_argument('--batch', action='store_true', help='Mine grammar from all traces in directory')

    group_ctx = parser.add_mutually_exclusive_group(required=True)
    group_ctx.add_argument('--ctx-none', action='store_true', help='Ctx = None')
    group_ctx.add_argument('--ctx-coarse', action='store_true', help='Ctx = Caller')
    group_ctx.add_argument('--ctx-fine', action='store_true', help='Ctx = Call Path')
    group_ctx.add_argument('--ctx-window', action='store_true', help='Ctx = Sliding window of call sites; k defined in .py')

    parser.add_argument('--token-cursor', action='store_true', dest='isTokenCursor', help='Set if subject is a token cursor subject')
    parser.add_argument('--token-grammar', type=str, help='Supply the token grammar (JSON) if subject is a token cursor subject')

    parser.add_argument('--scc', type=str, help='Supply the strongly connected components (JSON) if available.')
    parser.add_argument('--simplify', action='store_true', help='Simplify grammar (inline, opt generalization)')

    parser.add_argument('path', action='store', type=str, help='The path to trace / trace directory')

    args = parser.parse_args()

    assert not args.isTokenCursor or args.token_grammar

    if args.token_grammar:
        with open(args.token_grammar, "r") as f:
            token_grammar = json.load(f)
    else:
        token_grammar = None

    all_scc = None
    if args.scc:
        if os.path.exists(args.scc):
            with open(args.scc, "r") as f:
                scc = json.load(f)
                all_scc = [x for xs in scc.values() for x in xs] # all functions
            if all_scc == []:
                all_scc = None

    if args.ctx_none:
        ctx = CTX_NONE
    elif args.ctx_coarse:
        ctx = CTX_COARSE
    elif args.ctx_fine:
        ctx = CTX_FINE
    else:
        assert args.ctx_window
        ctx = CTX_WINDOW

    print(f"using ctx={ctx}")

    if args.single:
        fname = args.path
        with open(fname, "r") as f:
            j = json.load(f)

        exec_trace = ExecutionTrace(j, all_scc, fname)

        g = {}
        d_terminals = {}
        ctr_terminals = 0
        d_simplify_ctx = {}
        d_ctr_simplify_ctx = {}
        d_simple_loops = {}
        exec_tree = ExecutionTree(g, args.isTokenCursor, token_grammar, ctx, d_terminals, ctr_terminals, d_simplify_ctx, d_ctr_simplify_ctx, d_simple_loops)
        exec_tree.add_trace(exec_trace)
        g = exec_tree.to_grammar()
        print("g: ", json.dumps(g, indent=1))
        serialize_grammar(g, "single_grammar.json")
        tree = exec_tree.get()
        print("tree:")
        pprint(tree, width=1)
        display_tree(tree).render(filename='tree')
        print("serialized tree")

    else:
        directory = args.path
        exec_forest = ExecutionForest(directory, args.isTokenCursor, token_grammar, ctx, all_scc, simplify=args.simplify)
        g = exec_forest.get_grammar()
        serialize_grammar(g, "initial_grammar.json")
        print("Total traces: ", count_traces)
        print("Fixed traces: ", count_fixed_traces)
        print("Fixed positions: ", count_fixed_positions)


if __name__ == "__main__":
    main()