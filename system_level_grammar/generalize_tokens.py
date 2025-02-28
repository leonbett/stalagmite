import string
import re
import config
from typing import Type
import copy

from common import LimitFuzzer, is_nt
from collections import namedtuple

from generalize_helpers import replace_references

def is_external_function(s):
    return s.startswith('<__external_')

digits = {
    "<digits>": [["<digit>", "<digits>"], ["<digit>"]],
    "<digit>": [[c] for c in string.digits]
}

hex = {
    "<hex_0x>": [["0x", "<hexdigits>"]],
    "<hexdigits>": [["<hexdigit>", "<hexdigits>"], ["<hexdigit>"]],
    "<hexdigit>": [[c] for c in string.hexdigits]
}

float = {
    "<float_simple_1>": [["<opt_sign>", "<number>"]],
    "<float_simple_2>": [["<opt_sign>", "<number_simple>"]],
    "<float>": [["<opt_sign>", "<number>"], ["<opt_sign>", "<nan>"], ["<opt_sign>", "<inf>"]],
    "<opt_sign>": [[""], ["+"], ["-"]],

    "<number_simple>": [["<main_simple>", "<opt_exponent>"]],
    "<main_simple>": [["<digits>"], ["<digits>", ".", "<digits>"]], 

    "<number>": [["<main>", "<opt_exponent>"]], 
    "<main>": [["<digits>"], [".", "<digits>"], ["<digits>", ".", "<digits>"]], 
    "<opt_exponent>": [[""], ["<eE>" ,"<opt_sign>", "<digits>"]],

    "<eE>": [["e"], ["E"]],

    "<nan>": [["<nN>", "<aA>", "<nN>"]],
    "<nN>": [["n"], ["N"]],
    "<aA>": [["a"], ["A"]],

    "<inf>": [["<iI>", "<nN>", "<fF>"], ["<iI>", "<nN>", "<fF>", "<iI>", "<nN>", "<iI>", "<tT>", "<yY>"]],
    "<iI>": [["i"], ["I"]],
    "<nN>": [["n"], ["N"]],
    "<fF>": [["f"], ["F"]],
    "<tT>": [["t"], ["T"]],
    "<yY>": [["y"], ["Y"]],

    "<digits>": [["<digit>" ,"<digits>"], ["<digit>"]],
    "<digit>": [[c] for c in string.digits]
}

lower_ascii_str = {
    "<lower_ascii_str>": [["<lower_ascii_char>", "<lower_ascii_str>"], ["<lower_ascii_char>"]],
    "<lower_ascii_char>": [[c] for c in string.ascii_lowercase]
}

upper_ascii_str = {
    "<upper_ascii_str>": [["<upper_ascii_char>", "<upper_ascii_str>"], ["<upper_ascii_char>"]],
    "<upper_ascii_char>": [[c] for c in string.ascii_uppercase]
}

ascii_str = {
    "<ascii_str>": [["<ascii_char>", "<ascii_str>"], ["<ascii_char>"]],
    "<ascii_char>": [[c] for c in string.ascii_letters]
}

control_str = {
    "<control_str>": [["<control_char>", "<control_str>"], ["<control_char>"]],
    "<control_char>": [[chr(i)] for i in range(1, 32)] + [chr(127)]
}

control_str_w_zero = { 
    "<control_str_w_zero>": [["<control_char_w_zero>", "<control_str_w_zero>"], ["<control_char_w_zero>"]],
    "<control_char_w_zero>": [[chr(i)] for i in range(32)] + [chr(127)]
}

whitespace_str = {
    "<ws_str>": [["<ws_char>", "<ws_str>"], ["<ws_char>"]],
    "<ws_char>": [[chr(i)] for i in [0x20, 0x09, 0x0a, 0x0b, 0x0c, 0x0d]]
}

ws_control_str = {
    "<ws_control_str>": [["<ws_control_char>", "<ws_control_str>"], ["<ws_control_char>"]],
    "<ws_control_char>": [[chr(i)] for i in [0x20, 0x09, 0x0a, 0x0b, 0x0c, 0x0d]] + [[chr(i)] for i in range(1, 32)] + [[chr(127)]]
}

ws_control_str_w_zero = {
    "<ws_control_str_w_zero>": [["<ws_control_char_w_zero>", "<ws_control_str_w_zero>"], ["<ws_control_char_w_zero>"]],
    "<ws_control_char_w_zero>": [[chr(i)] for i in [0x20, 0x09, 0x0a, 0x0b, 0x0c, 0x0d]] + [[chr(i)] for i in range(32)] + [[chr(127)]]
}

quoted_string = {
    "<quoted_string>": [["<single_quoted_string>"], ["<double_quoted_string>"]],
    "<single_quoted_string>": [["'", "<opt_quote_str_single>", "'"]],
    "<opt_quote_str_single>": [[""], ["<quote_str_single>"]],
    "<quote_str_single>": [["<quote_char_single>", "<quote_str_single>"], ["<quote_char_single>"]],
    "<quote_char_single>": [[chr(i)] for i in range(1, 256) if chr(i) not in ["'"]],

    "<double_quoted_string>": [['"', "<opt_quote_str_double>", '"']],
    "<opt_quote_str_double>": [[""], ["<quote_str_double>"]],
    "<quote_str_double>": [["<quote_char_double>", "<quote_str_double>"], ["<quote_char_double>"]],
    "<quote_char_double>": [[chr(i)] for i in range(1, 256) if chr(i) not in ['"']],
}

printable_str = {
    "<printable_str>": [["<printable_char>", "<printable_str>"], ["<printable_char>"]],
    "<printable_char>": [[chr(i)] for i in range(32, 127)]
}

any_str = {
    "<any_str>": [["<any_char>", "<any_str>"], ["<any_char>"]],
    "<any_char>": [[chr(i)] for i in range(1, 256)] # All chars except 0x00
}

Pattern = namedtuple('Pattern', ['regex', 'string_nt', 'char_nt', 'grammar'])

def is_simple_pattern(p: Pattern):
    return p.char_nt is not None

UNIQUE_ID = 0
def new_id():
    global UNIQUE_ID
    UNIQUE_ID += 1
    return UNIQUE_ID

patterns = [
    Pattern(r'\d+', '<digits>', '<digit>', digits),
    Pattern(r'[a-z]+', '<lower_ascii_str>', '<lower_ascii_char>', lower_ascii_str),
    Pattern(r'[A-Z]+', '<upper_ascii_str>', '<upper_ascii_char>', upper_ascii_str),
    Pattern(r'[a-zA-Z]+', '<ascii_str>', '<ascii_char>', ascii_str),
    Pattern(r'\s+', '<ws_str>', '<ws_char>', whitespace_str),
    Pattern(r'[\s\x00-\x1F\x7F]+', '<ws_control_str>', '<ws_control_char>', ws_control_str),
    Pattern(r'[-+]?(\d+(\.\d*)([eE][-+]?\d+)?)', '<float_simple_2>', None, float),
    Pattern(r'[-+]?((\d+(\.\d*)?|\.\d+)([eE][-+]?\d+)?)', '<float_simple_1>', None, float),
    Pattern(r'[-+]?(((\d+(\.\d*)?|\.\d+)([eE][-+]?\d+)?)|[nN][aA][nN]|[iI][nN][fF]|[iI][nN][fF][iI][nN][iI][tT][yY]).?', '<float>', None, float),
    Pattern(r'0x[0-9a-fA-F]+', '<hex_0x>', None, hex),
    Pattern(r'[0-9a-fA-F]+', '<hexdigits>', "<hexdigit>", hex),
    Pattern(r'\'.*\'', "<single_quoted_string>", None, quoted_string),
    Pattern(r'\".*\"', "<double_quoted_string>", None, quoted_string),
    Pattern(r'[\'\"].*[\'\"]', "<quoted_string>", None, quoted_string),
    Pattern(r'[ -~]+', '<printable_str>', '<printable_char>', printable_str),
    Pattern(r'.+', '<any_str>', '<any_char>', any_str), 
    # most general pattern must be last in list
]

_all_pattern_nts = list(digits.keys()) + list(hex.keys()) + list(float.keys()) + list(lower_ascii_str.keys()) +\
                   list(upper_ascii_str.keys()) + list(ascii_str.keys()) + list(control_str.keys()) +\
                   list(control_str_w_zero.keys()) + list(quoted_string.keys()) + list(printable_str.keys()) + list(any_str.keys())

all_pattern_nts = _all_pattern_nts + [f"<opt_{p[1:-1]}>" for p in _all_pattern_nts]

ALLOWED_TOKEN_MISMATCH_RATE = 0.05

def all_match(unique_strs: set[str], regexp: str):
    regexp = r'^' + regexp + r'$'
    mismatches = 0
    for s in unique_strs:
        if not re.match(regexp, s, re.DOTALL): # re.DOTALL => `.` also matches NEWLINE
            mismatches += 1
            if mismatches/len(unique_strs) >= ALLOWED_TOKEN_MISMATCH_RATE:
                # If less than 5% mismatches, we still consider this "all match".
                # The reason is that sometimes there can be minor difference in the implementation vs pattern grammar.
                return False
    return True

ws_chars = ''.join([chr(i) for i in [0x20, 0x09, 0x0a, 0x0b, 0x0c, 0x0d]])
control_chars = ''.join([chr(i) for i in range(1, 32)] + [chr(127)])
ws_control_chars = ws_chars + control_chars
def strip_inputs(strings: set):
    lstripped_strings = set()
    ws_prefixes = []
    for s in strings:
        lstripped = s.lstrip(ws_control_chars)
        if lstripped != s:
            if lstripped == '':
                # The string consists exclusively of whitespaces -> workaround for s.find
                ws_prefix = s
            else:
                ws_prefix = s[:s.find(lstripped)]
            ws_prefixes.append(ws_prefix)
        lstripped_strings.add(lstripped)

    ws_alphabet = set(ws_char for ws_prefix in ws_prefixes for ws_char in ws_prefix) 
    return ws_alphabet, ws_prefixes, lstripped_strings

WS_CTR: int = 0
ws_set_to_id = dict()
# This function adds a custom optional whitespace string before the grammar (char and string grammar) in `pattern`.
def ws_grammar(pattern: Pattern, ws_set):
    global ws_set_to_id, WS_CTR

    ws_tup = tuple(sorted(list(ws_set)))
    if ws_tup not in ws_set_to_id:
        WS_CTR += 1
        ws_set_to_id[ws_tup] = WS_CTR
    
    ws_id: int = ws_set_to_id[ws_tup]

    custom_ws_grammar = {
        f"<ws{ws_id}_str>": [[f"<ws{ws_id}_char>", f"<ws{ws_id}_str>"], [f"<ws{ws_id}_char>"]],
        f"<ws{ws_id}_char>": [c for c in ws_set]
    }
    
    pre_ws_regex = rf'[{"".join(c for c in ws_set)}]*' + pattern.regex

    pre_ws_string_nt = f"<pre_ws_{pattern.string_nt[1:-1]}>"
    pre_ws_grammar = {**pattern.grammar,
                      **custom_ws_grammar,
                      pre_ws_string_nt: [[pattern.string_nt], [f"<ws{ws_id}_str>", pattern.string_nt]]} # <ws_str> is optional
    if pattern.char_nt is not None:
        pre_ws_char_nt = f"<pre_ws_{pattern.char_nt[1:-1]}>"
        pre_ws_grammar = {**pre_ws_grammar,
                          pre_ws_char_nt: [[pattern.char_nt], [f"<ws{ws_id}_str>", pattern.char_nt]]}
    else:
        pre_ws_char_nt = None
    return Pattern(pre_ws_regex, pre_ws_string_nt, pre_ws_char_nt, pre_ws_grammar)

NonTerminal = Type[str]
Grammar = Type[dict]

nt_ctr = 0
def new_nt() -> NonTerminal:
    global nt_ctr
    nt_ctr += 1
    # not "<nt{nt_ctr}>" to avoid name clashes
    return f"<toknt{nt_ctr}>"

def concrete_grammar(unique: set[str]) -> tuple[NonTerminal, Grammar]:
    start_nt = new_nt()
    alts = [[u] for u in unique]
    pattern_grammar = {start_nt: alts}
    return start_nt, pattern_grammar

def generate_inputs(fuzzer, nt, num_inputs=1000, max_depth=10):
    inputs: set[str] = set()
    for _ in range(num_inputs):
        inp, _ = fuzzer.fuzz(nt, max_depth=max_depth)
        inputs.add(inp)
    return inputs

def get_nt_alphabet(g, nt) -> set:
    # Get all terminals
    visited = set()
    alphabet = set()
    q = [nt]
    while q != []:
        cur_nt = q.pop()
        visited.add(cur_nt)
        for rule in g[cur_nt]:
            for tok in rule:
                if not is_nt(tok):
                    for c in tok:
                        alphabet.add(c)
                else:
                    if tok not in visited:
                        q.append(tok)
    return alphabet

def generalize_concrete_with_ws(nt, stripped_inputs, ws_alphabet):
    start, pattern_grammar = concrete_grammar(stripped_inputs)
    regex = f'({"|".join(stripped_inputs)})'
    pattern = Pattern(regex, start, None, pattern_grammar)
    _p = ws_grammar(pattern, ws_alphabet)
    grammar = _p.grammar
    start = _p.string_nt
    grammar[nt] = [[start]]
    print(f"Generalized {nt} to: {stripped_inputs} + leading WS")
    return grammar

def generalize_patterns(_g, nt, inputs, ws_alphabet, ws_prefixes, token_to_alphabet: None) -> dict:
    g = {}
    pattern: Pattern
    for pattern in patterns:
        if is_simple_pattern(pattern):
            isTokenCursor = bool(token_to_alphabet)
            if isTokenCursor:
                token_alphabet: set = token_to_alphabet[nt]
            else:
                token_alphabet = get_nt_alphabet(_g, nt)
        
            pattern_alphabet = set(ll[0] for ll in pattern.grammar[pattern.char_nt])
            print("DBG: token alphabet: ", token_alphabet)
            print("DBG: pattern alphabet: ", pattern_alphabet)
            if (token_alphabet != pattern_alphabet and
                token_alphabet.issubset(pattern_alphabet)):
                print("DBG: proper subset token alphabet: ", token_alphabet)
                print("DBG: proper diff token alphabet: ", pattern_alphabet - token_alphabet)

                refined_pattern = copy.deepcopy(pattern)
                refined_pattern.grammar[pattern.char_nt] = [[c] for c in sorted(list(token_alphabet))]
                # Update all NT names in the grammar with unique suffix, so subsequent generalization are not affected or override.
                next_id: int = new_id()
                nts = refined_pattern.grammar.keys()
                rpg = refined_pattern.grammar
                for __nt in nts:
                    rpg = replace_references(rpg, __nt, f"{__nt[:-1]}_{next_id}>")
                rpg = {f"{__nt[:-1]}_{next_id}>": rpg[__nt] for __nt in nts}
                pattern = Pattern(rf'[{"".join(re.escape(c) for c in token_alphabet)}]+',
                                  f"{pattern.string_nt[:-1]}_{next_id}>",
                                  f"{pattern.char_nt[:-1]}_{next_id}>",
                                  rpg)


        candidates: list[Pattern] = [pattern]
        if pattern.grammar not in [whitespace_str, control_str, ws_control_str]:
            # We require this *threshold* to distinguish optional leading spaces from "the odd space" originating from an <any_str>
            if len(ws_prefixes) >= len(inputs) * config.WS_RATIO:
                ws_p = ws_grammar(pattern, ws_alphabet)
                candidates.append(ws_p)

        for pc in candidates:
            if all_match(inputs, pc.regex):
                g.update(pc.grammar)
                g[nt] = [[pc.string_nt]]
                print(f"Generalized {nt} to {pc.string_nt}")
                return g
            
    assert False, "Error: generalize_patterns() should not read this point."


GENERALIZATION_THRESHOLD = 10
def generalize_tokens(g, token_to_alphabet: dict = None):
    fuzzer = LimitFuzzer(g)
    new_g = {}

    for nt, rules in g.items():
        if not is_external_function(nt):
            new_g[nt] = rules
            continue

        print("DBG: generalize_tokens of nt=", nt)
    
        inputs: set[str] = generate_inputs(fuzzer, nt)
        ws_alphabet, ws_prefixes, stripped_inputs = strip_inputs(inputs)

        # Case 1: concrete (keywords) w/ leading ws
        # We require this *threshold* to distinguish this from "the odd space" originating from a <any_str>
        if len(ws_prefixes) >= len(inputs)*config.WS_RATIO:
            if len(stripped_inputs) <= GENERALIZATION_THRESHOLD:
                new_g = {**new_g, **generalize_concrete_with_ws(nt, stripped_inputs, ws_alphabet)}
                print("DBG: generalize_tokens of nt=", nt, "case 1")
                continue

        # Case 2: concrete (keywords) w/o leading ws
        if len(inputs) <= GENERALIZATION_THRESHOLD:
            new_g[nt] = rules
            print(f"Did not generalize {nt} (<10 inputs). It remains: ", rules)
            print("DBG: generalize_tokens of nt=", nt, "case 2")

        # Case 3: abstract pattern
        # Case 4: abstract pattern w/ leading ws
        else:
            new_g = {**new_g, **generalize_patterns(g, nt, inputs, ws_alphabet, ws_prefixes, token_to_alphabet)}
            print("DBG: generalize_tokens of nt=", nt, "case 3")
            assert nt in new_g


    return new_g