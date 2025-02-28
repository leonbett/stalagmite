from collections import namedtuple
import sys
import copy
import signal
import time

import config
from typing import Union
from common import put_can_parse, is_nt, tree_to_str, LimitFuzzer
from generalize_helpers import serialize_grammar, load_json_file, replace_references

from fuzzingbook.Parser import IterativeEarleyParser

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
    parser = IterativeEarleyParser(updated_grammar, canonical=True)
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

def replace_in_rule(replace, replace_with, rule):
    new_rule = [tok if tok!=replace else replace_with for tok in rule]
    return new_rule

def does_not_introduce_infinite_loop(node, ruleset):
    if ruleset == [] or ruleset == [[]]: return True
    for rule in ruleset:
        if node not in rule:
            return True
    return False

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

# For each "rule" for node, generate K subtrees.
# Store: "rule": parsed/K
# Return the best "rule" with parsed/K to parent
def evaluate_rule_quality(grammar, node, fuzzer, orig_tree, path, put):
    rule_quality = [(rule, 0) for rule in grammar[node]]
    for choice in range(len(grammar[node])):
        for i in range(config.k_subtrees):
            inp, subtree = fuzzer.fuzz(key=node, first_choice=choice)
            new_tree = replace_path(copy.deepcopy(orig_tree), path, subtree)
            if put_can_parse(put, tree_to_str(new_tree)):
                rule_quality[choice] = (rule_quality[choice][0], rule_quality[choice][1] + 1)
    return rule_quality

def fuzz_alarm_handler(signum, frame):
    raise TimeoutException("Fuzzer timed out")

RefinementResult = namedtuple('RefinementResult', ['refinement_grammar', 'refined_nt', 'quality', 'success'])
class GrammarRefiner:
    def __init__(self, grammar_file, put, output_grammar_file=None):
        self.grammar_file = grammar_file
        self.grammar: dict = load_json_file(grammar_file)
        self.put = put
        self.output_grammar_file = output_grammar_file

        # Inputs which show that a grammar change is underapproximating will be added here, as an optimization for further refinement attempts.
        self.valid_discriminating_inputs = []

    def generate_and_classify_inputs(self, grammar, count):
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

            can_parse = put_can_parse(self.put, inp)
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


    def evaluate_and_refine_rule_alternatives(self, orig_tree, grammar, node, fuzzer, valid_inputs, path):
        rule_quality = evaluate_rule_quality(grammar, node, fuzzer, orig_tree, path, self.put)
        print(f"Rule quality list for node {node}: {rule_quality}", flush=True)

        max_quality = max(rule_quality, key=lambda x: x[1])[1]
        best_rules = [rule for rule, quality in rule_quality if quality == max_quality]
        refinement_grammar = {node: best_rules}

        if sorted(best_rules) != sorted(grammar[node]) and \
            does_not_introduce_infinite_loop(node, best_rules) and \
            max_quality > 0 and \
            not is_underapproximating(grammar, refinement_grammar, valid_inputs, self.valid_discriminating_inputs):
            # Here, we're refining node itself, not adding a refined_nt def.
            return RefinementResult(refinement_grammar, node, max_quality, True)
        else:
            refined_nt = refine_nt(node)
            refinement_grammar = {refined_nt: best_rules}
            print(f"(cur node: {node}) returning best_rules: {best_rules}, all with quality {max_quality}", flush=True)
            return RefinementResult(refinement_grammar, refined_nt, max_quality, False)

    def refine_in_parent_context(self, cur_tree, grammar, best_result, best_refinement_idx, valid_inputs):
        node, children = cur_tree

        updated_rule = []
        for i, c in enumerate(children):
            if i != best_refinement_idx:
                updated_rule.append(c[0])
            else:
                updated_rule.append(best_result.refined_nt)

        current_rule = [c[0] for c in children]
        refinement_grammar = {node: [rule if rule != current_rule else updated_rule for rule in grammar[node]]}
        refinement_grammar = {**best_result.refinement_grammar, **refinement_grammar}

        if not is_underapproximating(grammar, refinement_grammar, valid_inputs, self.valid_discriminating_inputs):
            # Here, we're refining node itself, not adding a refined_nt def.
            return RefinementResult(refinement_grammar, node, best_result.quality, True)
        else:
            refined_nt = refine_nt(node)
            refinement_grammar = {refined_nt: [replace_in_rule(replace=node, replace_with=refined_nt, rule=rule) if rule != current_rule else updated_rule for rule in grammar[node]]}
            refinement_grammar = {**best_result.refinement_grammar, **refinement_grammar}
            return RefinementResult(refinement_grammar, refined_nt, best_result.quality, False)    


    def refine_bottomup(self, orig_tree, cur_tree, grammar, fuzzer, inp, valid_inputs, path=None):
        if path == None:
            path = []
        
        node, children = cur_tree
        print("refine_bottomup called on node: ", node)

        # Recursion anchor: Terminals cannot be refined.
        if not is_nt(node):
            return RefinementResult(refinement_grammar=None, refined_nt=None, quality=-1, success=False)
        
        # Recursion: Traverse children first
        best_refinements = []
        for i, c in enumerate(children):
            rr: RefinementResult = self.refine_bottomup(orig_tree, c, grammar, fuzzer, inp, valid_inputs, path+[i]) # the best (rule, quality) tuple of each child
            best_refinements.append(rr)
            if rr.success: return rr

        # If we reach here, we have traversed all children, but refining the productions of the children did not yield a non-underapproximating refinement.
        # Here, we're checking if applying children refinements to the current node itself yields a non-underapproximating refinement.
        print("Current root: ", node)
        if best_refinements:
            best_refinement_idx = best_refinements.index(max(best_refinements, key=lambda x: x.quality))
            best_result = best_refinements[best_refinement_idx]
            if best_result.quality > 0:
                return self.refine_in_parent_context(cur_tree, grammar, best_result, best_refinement_idx, valid_inputs)
                
        # Base case: Children could not make the input "parse", so we try different *rules* for the current node.
        return self.evaluate_and_refine_rule_alternatives(orig_tree, grammar, node, fuzzer, valid_inputs, path)


    def refine_grammar_for_input(self, grammar, inp, valid_inputs) -> Union[dict, None]:
        parser = IterativeEarleyParser(grammar, canonical=True)

        signal.signal(signal.SIGALRM, alarm_handler)
        signal.alarm(config.parse_timeout_seconds)
        try:
            tree = next(parser.parse(inp))
        except TimeoutException:
            print('Timeout in refine_grammar_for_input. Returning.')
            return None
        finally:
            signal.alarm(0)

        fuzzer = LimitFuzzer(grammar)
        tree = tree[1][0]
        orig_tree = copy.deepcopy(tree)

        refinement_grammar, refined_nt, max_quality, success = self.refine_bottomup(orig_tree, tree, grammar, fuzzer, inp, valid_inputs)
        if not success: return None

        refined_grammar = {**grammar, **refinement_grammar}
        dedup_refined_grammar = refined_grammar
        # dedup until no change
        while (deduped := dedup(refined_grammar)) != dedup_refined_grammar:
            dedup_refined_grammar = deduped
        return dedup_refined_grammar

    def refine_grammar_once(self, grammar: dict) -> Union[dict, None]:
        self.valid_discriminating_inputs = list(set(self.valid_discriminating_inputs))
        valid_inputs, invalid_inputs = self.generate_and_classify_inputs(grammar, config.cnt_inputs_refinement)
        current_precision = len(valid_inputs)/(len(valid_inputs)+len(invalid_inputs))

        if current_precision >= config.precision_threshold:
            print("Reached precision >= config.precision_threshold -- Stopping.")
            return None

        l_valid_inputs = list(valid_inputs)
        l_valid_inputs.sort(key=len)
        invalid_inputs.sort(key=len)
        for inp in invalid_inputs[:config.k_shortest]:
            print("Trying to refine based on input: ", repr(inp), flush=True)
            refined_grammar = self.refine_grammar_for_input(grammar, inp, l_valid_inputs)
            if refined_grammar: return refined_grammar

        print("Unable to find refineable input", flush=True)
        return None

    def refine_grammar(self):
        grammar = self.grammar

        start = time.time()

        refinements = -1
        while (grammar and
               refinements < config.max_refinements and
               time.time() - start < config.max_refinement_time_seconds):
            refinements += 1
            if refinements: serialize_grammar(grammar, f"refined_grammar_{refinements}.json")
            print("Refinements: ", refinements, flush=True)
            final_grammar = grammar
            grammar = self.refine_grammar_once(grammar)


        serialize_grammar(final_grammar, "refined_grammar_final.json")
        if self.output_grammar_file:
            serialize_grammar(final_grammar, self.output_grammar_file)

        print(f"Final grammar after {refinements} refinements and {time.time() - start} seconds serialized.", flush=True)


def main():
    if len(sys.argv) != 3:
        print("Usage: python3 reduce_overapproximation.py <grammar.json> <program_under_test>", flush=True)
        sys.exit(1)
    
    grammar_file = sys.argv[1]
    put = sys.argv[2]

    gf = GrammarRefiner(grammar_file, put)
    gf.refine_grammar()

if __name__ == "__main__":
    main()