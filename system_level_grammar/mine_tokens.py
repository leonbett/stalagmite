import random
import json

import config

from generalize_helpers import load_jsons
from generalize_tokens import generalize_tokens

def build_token_dicts(d):
    d_token_to_samples = {}
    d_token_to_alphabet = {}
    for json_file_path, j in d.items():
        print(json_file_path)
        token_id = int(j["token_id"])
        del j["token_id"]
        if token_id not in d_token_to_samples:
            d_token_to_samples[token_id] = []
        if token_id not in d_token_to_alphabet:
            d_token_to_alphabet[token_id] = set()

        assert str(len(j)-1) in j, "last idx not in trace => not consecutive"

        # Delete (almost) unconstrained lookahead
        last_idx_solutions = j[str(len(j)-1)]["solutions"]
        if len(j) > 1 and len(last_idx_solutions) > config.last_char_solution_count_unconstrained:
            del j[str(len(j)-1)]

        # Delete trailing null byte
        last_idx_solutions = j[str(len(j)-1)]["solutions"]
        if len(j) > 1 and last_idx_solutions == [0]:
            del j[str(len(j)-1)]


        chars = []
        for i in range(len(j)):
            assert str(i) in j, "idx not in trace => not consecutive"
            orders = j[str(i)]["readorders"]
            ctxs = j[str(i)]["executioncontexts"]
            solutions = j[str(i)]["solutions"]
            assert solutions != []
            chars.append(random.choice(solutions)) # only add 1 solution, but add all solution characters to alphabet.
            for c in solutions:
                if c == 0: continue
                d_token_to_alphabet[token_id].add(chr(c))
        if chars not in d_token_to_samples[token_id]:
            d_token_to_samples[token_id].append(chars)
    return d_token_to_samples, d_token_to_alphabet

class TokenMiner:
    def __init__(self):
        self.log_file = "tokenklee.log"

    def mine_grammar(self):
        d_letters = load_jsons('reads-letters/')
        d_digits = load_jsons('reads-digits/')
        d_punctuation = load_jsons('reads-punctuation/')
        d_none = load_jsons('reads-none/')
        d = {**d_letters, **d_digits, **d_punctuation, **d_none}

        d_token_to_samples, d_token_to_alphabet = build_token_dicts(d)
        print("debug: d_token_to_samples: ")
        print(json.dumps(d_token_to_samples, indent=1), flush=True)

        g = {}
        token_to_alphabet = {}
        for token_id in sorted(d_token_to_samples.keys()):
            samples = d_token_to_samples[token_id]
            g[f"<__external_{token_id}>"] = [[''.join(chr(c) for c in s)] for s in samples] # This will be generalized (because __external)
            g[f"<TOK_{token_id}>"] = [[f"<__external_{token_id}>"]]
            token_to_alphabet[f"<__external_{token_id}>"] = d_token_to_alphabet[token_id]

        g = generalize_tokens(g, token_to_alphabet)
        
        with open(config.token_grammar_json, "w") as f:
            json.dump(g, f, indent=1)

        print(f"serialized token grammar to {config.token_grammar_json}")
        return g

    def mine(self):
        self.mine_grammar()

def main():
    print("Generating grammar from traces in reads-{letters,digits,punctuation,none}")
    tm = TokenMiner()
    tm.mine_grammar()

if __name__ == "__main__":
    main()
