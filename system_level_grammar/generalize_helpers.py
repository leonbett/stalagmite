import os
import json

####### <json load helpers> ##########

def list_files_in_directory(directory):
    return [f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))]

def load_json_file(file_path):
    with open(file_path, 'r') as file:
        return json.load(file)

def load_jsons(directory_path):
    d = {}
    files = list_files_in_directory(directory_path)

    # Load each JSON file
    for file_name in files:
        file_path = os.path.join(directory_path, file_name)
        if file_name.endswith('.json'):
            json_data = load_json_file(file_path)
            d[file_path] = json_data
    
    print(f"Loaded {len(files)} json files")
    return d

def serialize_grammar(grammar, path):
    with open(path, 'w') as f:
        json.dump(grammar, f, indent=1)
    print(f"Wrote grammar to {path}")

def print_grammar(name, grammar):
    print(f"{name}:")
    print(json.dumps(grammar, indent=1))

####### </json load helpers> ##########

####### <grammar helpers> ##########
def is_nt(s):
    return len(s) > 2 and s[0] == '<' and s[-1] == '>'

def reachable_nonterminals(grammar, start_symbol: str) -> set[str]:
    reachable = set()

    def _find_reachable_nonterminals(grammar, symbol):
        nonlocal reachable
        reachable.add(symbol)
        for rule in grammar[symbol]:
            for tok in rule:
                if is_nt(tok):
                    if tok not in reachable:
                        _find_reachable_nonterminals(grammar, tok)

    _find_reachable_nonterminals(grammar, start_symbol)
    return reachable

def unreachable_nonterminals(grammar, start_symbol) -> set[str]:
    return grammar.keys() - reachable_nonterminals(grammar, start_symbol)

def undefined_nts(grammar):
    all_nts = set()
    defined_nts = set()
    for key, rules in grammar.items():
        all_nts.add(key)
        defined_nts.add(key)
        for rule in rules:
            for elem in rule:
                if is_nt(elem):
                    all_nts.add(elem)
    return all_nts - defined_nts

def find_reachable_keys(grammar, key, reachable_keys=None, found_so_far=None):
    if reachable_keys is None: reachable_keys = {}
    if found_so_far is None: found_so_far = set()

    for rule in grammar[key]:
        for token in rule:
            if not is_nt(token): continue
            if token in found_so_far: continue
            found_so_far.add(token)
            if token in reachable_keys:
                for k in reachable_keys[token]:
                    found_so_far.add(k)
            else:
                keys = find_reachable_keys(grammar, token, reachable_keys, found_so_far)
    return found_so_far

def replace_references(grammar, replacee, replace_with):
    new_grammar = {}
    for key, ruleset in grammar.items():
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
####### </grammar helpers> ##########
