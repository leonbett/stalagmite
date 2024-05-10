import sys
import json
import copy
import os
import signal
import random
import time

import config
from common import put_can_parse, is_nt, tree_to_str, LimitFuzzer
from generalize_helpers import serialize_grammar

from fuzzingbook.Parser import IterativeEarleyParser, non_canonical


def get_child(tree, path):
    if not path: return tree # not([]) = True
    cur, *path = path
    return get_child(tree[1][cur], path)

def replace_path(tree, path, new_node=None):
    if new_node is None: new_node = []
    if not path: return copy.deepcopy(new_node)
    cur, *path = path
    name, children, *rest = tree
    new_children = []
    for i,c in enumerate(children):
        if i == cur:
            nc = replace_path(c, path, new_node)
        else:
            nc = c 
        if nc: 
            new_children.append(nc)
    return (name, new_children, *rest)

class TimeoutException(Exception):
    pass

def alarm_handler(signum, frame):
    raise TimeoutException("Parse function timed out")

def is_underapproximating(grammar, grammar_update, valid_inputs, valid_discriminating_inputs):
    print("is_underapproximating called on grammar_update: ", grammar_update, flush=True)
    updated_grammar = {**grammar, **grammar_update}
    nc_grammar = non_canonical(updated_grammar)
    parser = IterativeEarleyParser(nc_grammar)
    timeouts = 0
    for i, inp in enumerate(valid_discriminating_inputs+valid_inputs):
        print(f"is_underapproximating ({i}/{len(valid_discriminating_inputs+valid_inputs)}) trying to parse inp=", repr(inp), flush=True)
        signal.signal(signal.SIGALRM, alarm_handler)
        signal.alarm(config.parse_timeout_seconds)
        start = time.time()
        try:
            next(parser.parse(inp))
        except (SyntaxError, StopIteration):
            print("is_underapproximating=True (could not parse  input: ", repr(inp), ")")
            valid_discriminating_inputs.append(inp)
            return True
        except TimeoutException:
            print('Timeout, skip parsing of: ', inp, flush=True)
            timeouts += 1
            if config.stop_after_k_timeouts == timeouts:
                break
        finally:
            signal.alarm(0)
            print("is_underapproximating; parsing of cur input took ", time.time() - start, " s")
    print("is_underapproximating=False")
    return False

def replace_references(pruned_grammar, replacee, replace_with):
    new_grammar = {}
    for key, ruleset in pruned_grammar.items():
        new_ruleset = []
        for rule in ruleset:
            new_rule = []
            for tok in rule:
                if tok == replacee:
                    new_rule.append(replace_with)
                else:
                    new_rule.append(tok)
            new_ruleset.append(new_rule)
        new_grammar[key] = new_ruleset
    return new_grammar



def dedup(grammar):
    pruned_grammar = copy.deepcopy(grammar)

    dup = {} # maps values to keys
    for key, l_value in grammar.items():
        value = tuple(tuple(l) for l in l_value)
        if value not in dup:
            dup[value] = key
        else:
            # ruleset already exists
            del pruned_grammar[key]
            existing_key = dup[value]
            pruned_grammar = replace_references(pruned_grammar, replacee=key, replace_with=existing_key)

    return pruned_grammar



refinements = {}
def refine_nt(nt: str):
    assert is_nt(nt)
    if nt not in refinements:
        refinements[nt] = 0
    else:
        refinements[nt] += 1
    return f"<{nt[1:-1]}_refined_{refinements[nt]}>"

# The returned tuples are:
# (rule, quality_rule, grammar_update)
# If grammar_update is set, we terminate.
# If grammar_update is None at the end: could not reduce overapprox.
def bottomup_traversal(orig_tree, cur_tree, grammar, fuzzer, put, inp, valid_inputs, valid_discriminating_inputs, path = None):
    # orig_tree is never changed.
    if path == None:
        path = []
    
    node, children = cur_tree
    print("bottomup_traversal called on node: ", node)
    if not is_nt(node): # terminal
        print("returning early because node ", node, " is a terminal", flush=True)
        return (None, None, 0, False) # Nothing found
    
    # Recursion:
    best_refinements_quality = []
    for i, c in enumerate(children):
        refinement_grammar, refined_nt, quality, success = bottomup_traversal(orig_tree, c, grammar, fuzzer, put, inp, valid_inputs, valid_discriminating_inputs, path+[i]) # the best (rule, quality) tuple of each child
        best_refinements_quality.append((refinement_grammar, refined_nt, quality)) 
        if success: return refinement_grammar, refined_nt, quality, success

    # Current root:
    print("current root: ", node)
    if best_refinements_quality != []:
        # We have to check for `best_refinements_quality` not being empty because "eps" productions look like <some_nt> -> [], not <some_nt> -> None
        # due to a bug in EarleyParser.
        best_refinement_idx = best_refinements_quality.index(max(best_refinements_quality, key=lambda x: x[2]))
        # Multiple children might have the same quality, so we might also consider multiple rulesets here.
        best_refinement_grammar, best_refined_nt, best_rule_quality = best_refinements_quality[best_refinement_idx]
    if best_refinements_quality != [] and best_rule_quality > 0:
        # As soon as one non-zero quality child is found, we should simply *propagate* the best child's rule in the context of the *nodes* rule.
        # Note: Now we have potentially multiple best rules though for one child.
        # We currently simply return the first non-underapproximating one. There are potentially more "best non-underapproximating" ones though.
        updated_rule = []
        for i, c in enumerate(children):
            if i != best_refinement_idx:
                updated_rule.append(c[0])
            else:
                updated_rule.append(best_refined_nt)

        current_rule = [c[0] for c in children]
        refinement_grammar = {node: [rule if rule != current_rule else updated_rule for rule in grammar[node]]}
        refinement_grammar = {**best_refinement_grammar, **refinement_grammar}

        if not is_underapproximating(grammar, refinement_grammar, valid_inputs, valid_discriminating_inputs):
            # Here, we're refining node itself, not adding a refined_nt def.
            return refinement_grammar, node, best_rule_quality, True # True means success
        else:
            refined_nt = refine_nt(node)
            refinement_grammar = {refined_nt: [rule if rule != current_rule else updated_rule for rule in grammar[node]]}
            refinement_grammar = {**best_refinement_grammar, **refinement_grammar}
            print(f"(could not find underapproximating grammar update at this depth node: {node}) returning a refinement_grammar with quality {best_rule_quality}", flush=True)
            return refinement_grammar, refined_nt, best_rule_quality, False
            
    else:
        # Children could not make the input "parse", so we try different *rules* for the current node.

        # For each "rule" for node, generate K subtrees.
        # Store: "rule": parsed/K
        # Return the best "rule" with parsed/K to parent
        cnt_rules = len(grammar[node]) # canonical grammar
        rule: list
        rule_quality = [(rule, 0) for rule in grammar[node]]
        for choice in range(cnt_rules):
            for i in range(config.k_subtrees):
                inp, subtree = fuzzer.fuzz(key=node, first_choice=choice)
                new_tree = replace_path(copy.deepcopy(orig_tree), path, subtree)
                if put_can_parse(put, tree_to_str(new_tree)):
                    rule_quality[choice] = (rule_quality[choice][0], rule_quality[choice][1]+1)
        
        print(f"for node: {node}, rule quality list: {rule_quality}", flush=True)
        # Return the best rule
        max_quality = max(rule_quality, key=lambda x: x[1])[1]
        best_rules = [rule for rule, quality in rule_quality if quality == max_quality]
        refinement_grammar = {node: best_rules}
        if max_quality > 0 and not is_underapproximating(grammar, refinement_grammar, valid_inputs, valid_discriminating_inputs):
            # Here, we're refining node itself, not adding a refined_nt def.
            return refinement_grammar, node, max_quality, True # True means success
        else:
            refined_nt = refine_nt(node)
            refinement_grammar = {refined_nt: best_rules}
            print(f"(cur node: {node}) returning best_rules: {best_rules}, all with quality {max_quality}", flush=True)
            return refinement_grammar, refined_nt, max_quality, False


def bottomup(grammar, nc_grammar, put, inp, valid_inputs, valid_discriminating_inputs):
    parser = IterativeEarleyParser(nc_grammar)
    print("nc_grammar: ", nc_grammar, flush=True)
    tree = next(parser.parse(inp))
    fuzzer = LimitFuzzer(grammar)
    tree = tree[1][0]
    print("tree: ", tree, flush=True)

    orig_tree = copy.deepcopy(tree)

    refinement_grammar, refined_nt, max_quality, success = bottomup_traversal(orig_tree, tree, grammar, fuzzer, put, inp, valid_inputs, valid_discriminating_inputs)
    if success:
        print("bottomup_traversal grammar update: ", refinement_grammar, flush=True) # refinement grammar is the minimal update
        refined_grammar = {**grammar, **refinement_grammar}
        dedup_refined_grammar = refined_grammar
        # dedup until no change
        while (deduped := dedup(refined_grammar)) != dedup_refined_grammar:
            dedup_refined_grammar = deduped
        return dedup_refined_grammar
    else:
        return None

def fuzz_alarm_handler(signum, frame):
    raise TimeoutException("Fuzzer timed out")

def generate_and_classify_inputs(grammar, put, count):
    f = LimitFuzzer(grammar)
    valid = set()
    invalid = set()
    i = 0
    while i < count or len(valid) < config.min_count_valid:
        signal.signal(signal.SIGALRM, fuzz_alarm_handler)
        signal.alarm(1)
        try:
            inp, tree = f.fuzz()
        except TimeoutException:
            print('Timeout in generate_and_classify_inputs')
            continue
        finally:
            signal.alarm(0)

        can_parse = put_can_parse(put, inp)
        if can_parse == None: continue # core dumped, e.g. div-by-zero / semantic error
        elif can_parse == False:
            invalid.add(inp)
        else:
            valid.add(inp)
        i += 1

    print("valid inputs: ", valid)
    print("invalid inputs: ", invalid)
    print(f"Precision ({len(valid)}/{len(valid)+len(invalid)})", flush=True)

    return list(valid), list(invalid)

def refine(subject: str, grammar_file: str, put: str):
    with open(grammar_file, 'r') as f:
        grammar = json.load(f)
        nc_grammar = non_canonical(grammar)

    final_grammar = grammar

    l_valid_discriminating_inputs = [] # Inputs which show that a grammar change is underapproximating will be added here, as an optimization for further refinement attempts.
    
    # Keep refining until [1] precision threshold reached, or [2] config.max_refinements reached, or [3] no refinement possible
    refinements = 0
    while refinements < config.max_refinements: # [2]
        print("Refinements: ", refinements, flush=True)
        l_valid_discriminating_inputs = list(set(l_valid_discriminating_inputs)) # de-dup, inputs are added in is_underapproximating
        valid_inputs, invalid_inputs = generate_and_classify_inputs(grammar, put, config.cnt_inputs_refinement)
        precision = len(valid_inputs)/(len(valid_inputs)+len(invalid_inputs))
        if precision >= config.precision_threshold: # [1]
            print("Reached precision >= config.precision_threshold -- Stopping.")
            break

        l_valid_inputs = list(valid_inputs)
        l_valid_inputs.sort(key=len) # Sorting these as short inputs should parse faster
        invalid_inputs.sort(key=len)
        for inp in invalid_inputs[:config.k_shortest]:
            print("Trying to refine based on input: ", repr(inp), flush=True)
            refined_grammar = bottomup(grammar, nc_grammar, put, inp, l_valid_inputs, l_valid_discriminating_inputs)
            if refined_grammar:
                with open(f"refined_grammar_{refinements}.json", "w") as f:
                    json.dump(refined_grammar, f, indent=1)
                refinements += 1
                final_grammar = refined_grammar
                grammar = refined_grammar
                nc_grammar = non_canonical(refined_grammar)
                break
        if not refined_grammar: # [3]
            print("Unable to find refineable input", flush=True)
            break

    serialize_grammar(final_grammar, "refined_grammar_final.json")
    serialize_grammar(grammar, os.path.join(config.grammars_refined_dir, f"refined_grammar_{subject}.json"))

    print(f"Final grammar after {refinements} refinements serialized.", flush=True)


def main():
    if len(sys.argv) != 4:
        print("Usage: python3 reduce_overapproximation.py <subject> <grammar.json> <program_under_test>", flush=True)
        sys.exit(1)
    
    subject = sys.argv[1]
    grammar_file = sys.argv[2]
    put = sys.argv[3]

    refine(subject, grammar_file, put)

if __name__ == "__main__":
    main()