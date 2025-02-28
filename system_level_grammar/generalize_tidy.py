import copy
from itertools import combinations

from generalize_tokens import patterns
from generalize_helpers import is_nt

def inline_single_rules_and_opt_generalization(grammar):
    # Do (inline fix point, opt fix point) in another fix point loop,
    # as they depend on each other.
    global_change = True
    while global_change:
        global_change = False
        # Inline single rule non-terminals.
        # Fix-point iteration, because inlined rules, in turn, can have inlineable nts.
        change = True
        while change:
            grammar, change = inline_single_rule_nts(grammar)
            global_change = change

        # Do "<opt>" cleanup
        grammar, _global_change = opt_generalization(grammar)
        global_change |= _global_change

    return grammar

def inline_single_rule_nts(grammar):
    # We do not want to inline pattern nts,
    # to preserve their structure, and because
    # they could prevent some further opts.
    ignore_nts = [p[1] for p in patterns]

    change = False
    temp_grammar = {}
    for key, rules in grammar.items():
        temp_grammar[key] = []
        for rule in rules:
            new_rule = []
            for token in rule:
                if key not in ignore_nts and token not in ignore_nts and \
                    is_nt(token) and token in grammar and len(grammar[token])==1:
                    print(f"Inlining {token} to {grammar[token][0]}")
                    new_rule.extend(grammar[token][0])
                    change = True
                else:
                    new_rule.append(token)
            if new_rule not in temp_grammar[key]:
                # Avoid duplicates
                temp_grammar[key].append(new_rule)
    return temp_grammar, change

#<opt generalization>
def gen_dummy_rules(rule: list[str]):
    rules = []
    for i in range(len(rule)+1):
        new = rule[:i] + ["<dummy>"] + rule[i:]
        rules.append(new)
    return rules

def one_matches_modulo_dummy(rule, dummy_rules):
    match = True
    for dummy_rule in dummy_rules:
        assert len(rule) == len(dummy_rule)
        match = True
        for i in range(len(rule)):
            if rule[i] != dummy_rule[i] and dummy_rule[i] != "<dummy>":
                # actual mismatch
                match = False
                break
        if match: return dummy_rule
    return None

def opt_generalization(grammar):
    global_change = False
    temp_grammar = copy.deepcopy(grammar)
    g_keys = list(temp_grammar.keys())
    for key in g_keys:
        change = True
        while change:
            change = False
            # Check if any two rules are equal modulo a single optional NT (i.e. one rule is 1 element shorter)

            for (i, j) in combinations(range(len(temp_grammar[key])), 2):
                # unique pairs
                if abs(len(temp_grammar[key][i]) - len(temp_grammar[key][j])) == 1:
                    if len(temp_grammar[key][i]) < len(temp_grammar[key][j]):
                        short = i
                        long = j
                    else:
                        short = j
                        long = i
                    match_dummy_rule = one_matches_modulo_dummy(temp_grammar[key][long], gen_dummy_rules(temp_grammar[key][short]))
                    if match_dummy_rule:
                        dummy_idx = match_dummy_rule.index("<dummy>")
                        optional = temp_grammar[key][long][dummy_idx]
                        if not is_nt(optional): continue 
                        if optional.startswith("<opt_"): continue # We don't want <opt_opt_opt_...
                        print("Found optional element: ", optional)
                        assert optional[0] == "<" and optional[-1] == ">"
                        temp_grammar[key][long][dummy_idx] = f"<opt_{optional[1:-1]}>"
                        temp_grammar[f"<opt_{optional[1:-1]}>"] = [[""], [optional]]
                        # - Delete shorter rule
                        temp_grammar[key] = temp_grammar[key][:short] +  temp_grammar[key][short+1:]
                        change = True
                        global_change = True
                        break
    return temp_grammar, global_change
#</opt generalization>