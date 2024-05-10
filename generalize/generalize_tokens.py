import string
import re
from typing import Type
import copy

import config

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
    "<float>": [["<opt_sign>", "<number>"], ["<opt_sign>", "<nan>"], ["<opt_sign>", "<inf>"]],
    "<opt_sign>": [[""], ["+"], ["-"]],
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
    "<quoted_string>": [["'", "<opt_inside_str>", "'"], ['"', "<opt_inside_str>", '"']],
    "<opt_inside_str>": [[""], ["<non_quote_str>"]],
    "<non_quote_str>": [["<non_quote_char>", "<non_quote_str>"], ["<non_quote_char>"]],
    "<non_quote_char>": [[chr(i)] for i in range(1, 256) if chr(i) not in ["'", '"']]
}

printable_str = {
    "<printable_str>": [["<printable_char>", "<printable_str>"], ["<printable_char>"]],
    "<printable_char>": [[chr(i)] for i in range(32, 127)]
}

any_str = {
    "<any_str>": [["<any_char>", "<any_str>"], ["<any_char>"]],
    "<any_char>": [[chr(i)] for i in range(1, 256)] # All chars except 0x00
}

patterns = [
    (r'\d+', '<digits>', '<digit>', digits),
    (r'[a-z]+', '<lower_ascii_str>', '<lower_ascii_char>', lower_ascii_str),
    (r'[A-Z]+', '<upper_ascii_str>', '<upper_ascii_char>', upper_ascii_str),
    (r'[a-zA-Z]+', '<ascii_str>', '<ascii_char>', ascii_str),
    (r'\s+', '<ws_str>', '<ws_char>', whitespace_str),
    (r'[\s\x00-\x1F\x7F]+', '<ws_control_str>',  '<ws_control_char>', ws_control_str),
    (r'[-+]?(((\d+(\.\d*)?|\.\d+)([eE][-+]?\d+)?)|[nN][aA][nN]|[iI][nN][fF]|[iI][nN][fF][iI][nN][iI][tT][yY]).?', '<float>', None, float),
    (r'0x[0-9a-fA-F]+', '<hex_0x>', None, hex),
    (r'[0-9a-fA-F]+', '<hexdigits>', "<hexdigit>", hex),
    (r'[\'\"].*[\'\"]', "<quoted_string>", None, quoted_string),
    (r'[ -~]+', '<printable_str>', '<printable_char>', printable_str),
    (r'.+', '<any_str>', '<any_char>', any_str), 
    # most general pattern must be last in list
]

NonTerminal = Type[str]
Grammar = Type[dict]

ws_set_to_id = dict()

WS_CTR: int = 0
# This function adds a custom optional whitespace string before the grammar (char and string grammar) in `pattern`.
def ws_grammar(pattern, ws_set):
    global ws_set_to_id, WS_CTR
    regex, string_nt, char_nt, grammar = pattern

    ws_tup = tuple(sorted(list(ws_set)))
    if ws_tup not in ws_set_to_id:
        WS_CTR += 1
        ws_set_to_id[ws_tup] = WS_CTR
    
    ws_id: int = ws_set_to_id[ws_tup]

    custom_ws_grammar = {
        f"<ws{ws_id}_str>": [[f"<ws{ws_id}_char>", f"<ws{ws_id}_str>"], [f"<ws{ws_id}_char>"]],
        f"<ws{ws_id}_char>": [c for c in ws_set]
    }
    
    pre_ws_regex = rf'[{"".join(c for c in ws_set)}]*' + regex

    pre_ws_string_nt = f"<pre_ws_{string_nt[1:-1]}>"
    pre_ws_grammar = {**grammar,
                      **custom_ws_grammar,
                      pre_ws_string_nt: [[string_nt], [f"<ws{ws_id}_str>", string_nt]]} # <ws_str> is optional
    if char_nt is not None:
        pre_ws_char_nt = f"<pre_ws_{char_nt[1:-1]}>"
        pre_ws_grammar = {**pre_ws_grammar,
                          pre_ws_char_nt: [[char_nt], [f"<ws{ws_id}_str>", char_nt]]}
    else:
        pre_ws_char_nt = None
    return (pre_ws_regex, pre_ws_string_nt, pre_ws_char_nt, pre_ws_grammar)


def all_match(unique_strs: set[str], pattern: tuple):
    assert isinstance(pattern[0], str), "must be a regex"
    regex = r'^' + pattern[0] + r'$'
    print("debug pattern: ", pattern[0])
    mismatches = 0
    for s in unique_strs:
        if not re.match(pattern[0], s, re.DOTALL): # re.DOTALL => `.` also matches NEWLINE
            mismatches += 1
            if mismatches/len(unique_strs) >= config.ALLOWED_TOKEN_MISMATCH_RATE:
                # If less than 5% mismatches, we still consider this "all match".
                # The reason is that sometimes there can be minor difference in the implementation vs pattern grammar.
                return False
    return True

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


def optional_grammar(start_nt_seq, pattern_grammar):
    new_pattern_grammar = copy.deepcopy(pattern_grammar)
    new_pattern_nt = f"<expl_opt_{start_nt_seq[1:-1]}>" # different name so it can be <opt_expl_opt'd
    new_pattern_grammar[new_pattern_nt] = [[""], [start_nt_seq]]
    return new_pattern_nt, new_pattern_grammar

def generalize(conc_chars: list):
    """ conc_chars is a list of lists e.g.:
    [[32, 32, 127, 32],
    [32],
    [32, 127],
    [8],
    [32, 127, 127]]
    ...
    """
    ws_chars = ''.join([chr(i) for i in [0x20, 0x09, 0x0a, 0x0b, 0x0c, 0x0d]])
    control_chars = ''.join([chr(i) for i in range(1, 32)] + [chr(127)])
    ws_control_chars = ws_chars + control_chars

    # `ws_control_chars` is the total set of white space characters considered
    # Next, we find out if ws occur (often enough) at the left side.
    # We also find out if a specific character occurs often enough as part of a
    # whitespace prefix/suffix so it is considered part of the alphabet.

    strings = set()
    lstripped_strings = set()
    ws_prefixes = []

    # NOTE: only considering lstripped_strings
    for conc_num_str in conc_chars:
        s = ''.join(chr(c) for c in conc_num_str)
        strings.add(s)
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

    # <GENERALIZE_<=_THRESHOLD_GENERALIZATION_DIFFERENT_INSTANCES_WITH_WS>

    # First try with WS generalization, then without.
    if len(ws_prefixes) >= len(strings)*config.WS_RATIO:
        # We require this *threshold* to distinguish this from "the odd space" originating from a <any_str>
        if len(lstripped_strings) <= config.THRESHOLD_GENERALIZATION and not (len(lstripped_strings) == 1 and list(lstripped_strings)[0] == ""): # Second condition would imply that it's WS only, which is handled below.
            # Token instances were only > THRESHOLD_GENERALIZATION because of WS/ControlChars.
            start, pattern_grammar = concrete_grammar(lstripped_strings)
            regex = f'({"|".join(lstripped_strings)})'
            pattern = regex, start, None, pattern_grammar
            _p = ws_grammar(pattern, ws_alphabet)
            grammar = _p[-1]
            start = _p[1]
            return start, grammar
        
    elif len(strings) <= config.THRESHOLD_GENERALIZATION:
        # Nothing to do here
        return concrete_grammar(strings)

    # </GENERALIZE_<=_THRESHOLD_GENERALIZATION_DIFFERENT_INSTANCES_WITH_WS>

    # If we reach here, there > THRESHOLD_GENERALIZATION unique stripped token instances for this token, so we
    # generalize this token more.

    # Check if *all* instances of the token match a given regex.
    for p in patterns:
        pg = p[3]
        if pg == whitespace_str or pg == control_str or pg == ws_control_str:
            # We don't do further pre/post whitespace generalization for whitespace pattern grammars.
            candidates = [p]
        else:
            candidates = [p]
            if len(ws_prefixes) >= len(strings)*config.WS_RATIO:
                # We require this *threshold* to distinguish this from "the odd space" originating from a <any_str>
                ws_p = ws_grammar(p, ws_alphabet)
                print("debug: ws alphabet: ", ws_alphabet)
                print("debug: strings: ", strings)
                print("debug: lstripped_strings: ", lstripped_strings)
                print("debug: ws_prefixes: ", ws_prefixes)

                candidates.append(ws_p)

        for pc in candidates:
            if all_match(strings, pc):
                start_nt_seq = pc[1]
                start_nt_char = pc[2]
                pattern_grammar = pc[3]
                # We always generalize ws to "strings", never "chars". Here we handle the case that a token is only "ws", i.e. not the ws_grammar case.
                if start_nt_seq.startswith("<ws_"):
                    return start_nt_seq, pattern_grammar
                else:
                    if start_nt_char is not None:
                        if all(len(u) in [0,1] for u in lstripped_strings):
                            # All instances were a single character,
                            # so we don't generalize this to an arbitrary length string.
                            return start_nt_char, pattern_grammar
                return start_nt_seq, pattern_grammar
    # Could not be generalized
    return concrete_grammar(strings)

debug = True
def token_map_to_generalization(token_map):
    token_id_to_generalization = {}
    if debug: print("token_map:")
    for functionpath in token_map:
        if debug: print("functionpath: ", functionpath)
        for token_id in token_map[functionpath]:
            for conc_chars in token_map[functionpath][token_id]:
                if debug: print("\t", conc_chars)
            if debug: print("generalized to:")
            start_nt, pattern_grammar = generalize(token_map[functionpath][token_id])
            if debug: print("\t ", start_nt, pattern_grammar)
            if functionpath not in token_id_to_generalization:
                token_id_to_generalization[functionpath] = {}
            token_id_to_generalization[functionpath][token_id] = (start_nt, pattern_grammar)
    return token_id_to_generalization

EventTokenByteCursor = "EventTokenByteCursor"
def generalize_tokens(d_tokens: dict) -> dict:
    # token_map maps exec_ctx to all character instances of the exec_ctx.
    token_map = {}

    for filename, j in d_tokens.items(): # filename can be *_rep_1 also.
        events = j["events"]
        functionpath = j["functionpath"]
        for event in events:
            if event["event"] == EventTokenByteCursor:
                # filename <=> one execution path
                if functionpath not in token_map:
                    token_map[functionpath] = {}
                exec_ctx = event["exec_ctx"]
                if exec_ctx not in token_map[functionpath]:
                    token_map[functionpath][exec_ctx] = []
                token_map[functionpath][exec_ctx].append(event["concrete_characters"])

    return token_map_to_generalization(token_map)