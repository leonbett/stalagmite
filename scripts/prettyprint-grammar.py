import sys
import json

def is_nt(s):
    return len(s) > 2 and s[0] == '<' and s[-1] == '>'

def display_rule(rule, pre, verbose):
    if verbose > -1:
        v = (' '.join([t if is_nt(t) else repr(t) for t in rule]))
        s = '%s|   %s' % (pre, v)
        print(s)

def display_definition(grammar, key, r, verbose):
    if verbose > -1: print(key,'::=')
    for rule in grammar[key]:
        r += 1
        if verbose > 1:
            pre = r
        else:
            pre = ''
        display_rule(rule, pre, verbose)
    return r

#[x]
def recurse_grammar(grammar, key, order, undefined=None):
    undefined = undefined or {}
    rules = sorted(grammar[key])
    old_len = len(order)
    for rule in rules:
        for token in rule:
            if not is_nt(token): continue
            if token not in grammar:
                if token in undefined:
                    undefined[token].append(key)
                else:
                    undefined[token] = [key]
                continue
            if token not in order:
                order.append(token)
    new = order[old_len:]
    for ckey in new:
        recurse_grammar(grammar, ckey, order, undefined)
    return undefined

#[x]
def sort_grammar(grammar, start_symbol):
    order = [start_symbol]
    undefined = recurse_grammar(grammar, start_symbol, order)
    return order, [k for k in grammar if k not in order], undefined

#[x]
def display_grammar(grammar, start, tokens, verbose=0):
    r = 0
    k = 0
    order, not_used, undefined = sort_grammar(grammar, start)
    print('[start]:', start)
    for key in order:
        if key not in tokens:
            k += 1
            r = display_definition(grammar, key, r, verbose)
            if verbose > 0:
                print(k, r)

    if not_used and verbose > 0:
        print('[not_used]')
        for key in not_used:
            r = display_definition(grammar, key, r, verbose)
            if verbose > 0:
                print(k, r)
    if undefined:
        print('[undefined keys]')
        for key in undefined:
            if verbose == 0:
                print(key)
            else:
                print(key, 'defined in')
                for k in undefined[key]: print(' ', k)

    print('keys:', k, 'rules:', r)

def main():
    if len(sys.argv) < 2:
        print("Usage: prettyprint-grammar.py <grammar.json> (<tokens.json>)")
        print("If tokens.json is supplied, the definitions of these won't be printed")

    tokens = []
    if len(sys.argv) > 2:
        with open(sys.argv[2], "r") as f:
            tokens = list(json.load(f))

    grammar_path = sys.argv[1]
    start = "<start>"
    with open(grammar_path, "r") as f:
        grammar = json.load(f)

    display_grammar(grammar, start, tokens)

if __name__ == "__main__":
    main()