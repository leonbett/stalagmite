import sys
import json

# inspired by: https://rahul.gopinath.org/post/2021/09/09/fault-inducing-grammar/

debug = False

def is_nt(s):
    return len(s) > 2 and s[0] == '<' and s[-1] == '>'

def display_definition(grammar, key, r, rule_lengths):
    for rule in grammar[key]:
        r += 1
        rule_lengths.append(len(rule))
    return r, rule_lengths

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

def sort_grammar(grammar, start_symbol):
    order = [start_symbol]
    undefined = recurse_grammar(grammar, start_symbol, order)
    return order, [k for k in grammar if k not in order], undefined

def get_grammar_stats(grammar, start, tokens, verbose=0) -> tuple[int, int]:
    count_keys = 0
    count_rules = 0
    rule_lengths = []
    order, not_used, undefined = sort_grammar(grammar, start)
    for key in order:
        if key not in tokens:
            count_keys += 1
            count_rules, rule_lengths = display_definition(grammar, key, count_rules, rule_lengths)

    assert rule_lengths != []
    average_rule_length = sum(rule_lengths) / len(rule_lengths)
    sum_rule_lengths = sum(rule_lengths)
    return count_keys, count_rules, average_rule_length, sum_rule_lengths

def main():
    g = {
        "<start>": [["<a>"]],
        "<a>": [["<num>", "+", "<num>"], ["<num>", "-", "<num>"]],
        "<num>": [["1"], ["2"], ["3"], ["4"], ["5"], ["6"], ["7"], ["8"], ["9"], ["0"]]
    }
    print(get_grammar_stats(g, '<start>', []))
    print(get_grammar_stats(g, '<start>', ['<num>']))

if __name__ == "__main__":
    main()