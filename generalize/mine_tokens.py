import subprocess
import random
import json
import os

import config

from generalize_helpers import load_jsons
from generalize_tokens import generalize

EventCharacter = "EventCharacter"
EventPassToken = "EventPassToken"

def build_token_dicts(d):
    d_token_to_samples = {}
    d_token_to_alphabet = {}
    for key, j in d.items():
        events = j["events"]
        assert events[-1]["event"] == EventPassToken
        token_id: int = int(events[-1]['id'])
        if token_id not in d_token_to_samples:
            d_token_to_samples[token_id] = []
        if token_id not in d_token_to_alphabet:
            d_token_to_alphabet[token_id] = set()

        if len(events) == 1:
            # This is only an EventPassToken, i.e. no accepts, e.g. "EOF" token
            if [] not in d_token_to_samples[token_id]:
                d_token_to_samples[token_id].append([])
        else:
            chars = []
            accepts = events[:-1] # delete EventPassToken
            possible_solutions = accepts[-1]["possible_solutions"]
            if len(possible_solutions) > config.last_char_solution_count_unconstrained: # (almost) unconstrained lookahead
                accepts = accepts[:-1] # delete lookahead

            for event in accepts:
                assert event["event"] == EventCharacter
                solutions = event["possible_solutions"]
                assert solutions != []
                chars.append(random.choice(solutions)) # only add 1 solution, but add all solution characters to alphabet.
                for c in solutions:
                    d_token_to_alphabet[token_id].add(c)
            if chars not in d_token_to_samples[token_id]:
                d_token_to_samples[token_id].append(chars)
    return d_token_to_samples, d_token_to_alphabet

class TokenMiner:
    def __init__(self, tokenization_function: str):
        self.tokenization_function = tokenization_function
        self.log_file = "tokenklee.log"

    def run_klee(self, restriction: str):
        command = ["klee",
                   "--output-module",
                   "--libc=uclibc",
                   "--posix-runtime",
                   "--token-exploration-mode=true",
                   "--max-memory-inhibit=false", # don't kill states/stop forking
                   f"--max-memory={config.max_memory}",
                   f"--max-time={config.max_time_tokens}",
                   f"--parser-function-under-analysis=tok_{restriction}", # dummy, for output file name
                   f"--entry-point=kw_{self.tokenization_function}",
                   "--search=bfs",
                   "combined.bc",
                   f"{config.max_token_length}",
                   f"{restriction}"]
        # print("Running klee: ", command)
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        with open(self.log_file, "a") as f:
            f.write("Started klee with args: " + str(command))
            f.write(result.stderr + result.stdout)
        return result
    
    def clean(self):
        os.system(f"rm -rf {config.token_grammar_json} jsons* grammar* kleelog* genlog* {self.log_file}")
        os.system("make clean")
        os.system("make")

    '''Serializes jsons/.'''
    def generate_jsons(self):
        self.clean()
        for restriction in ["letters", "digits", "punctuation", "none"]:
            print(f"Exploring {self.tokenization_function} with restriction={restriction}", flush=True)
            self.run_klee(restriction)

    def mine_grammar(self):
        d = load_jsons('jsons/')
        d_token_to_samples, d_token_to_alphabet = build_token_dicts(d)
        print("debug: d_token_to_samples: ")
        print(json.dumps(d_token_to_samples, indent=1), flush=True)
        grammar = {}

        for token_id in sorted(d_token_to_samples.keys()):
            print(f"Generalizing token_id={token_id} to:")
            samples = d_token_to_samples[token_id]
            start_nt, pattern_grammar = generalize(samples)
            grammar = {**grammar, **pattern_grammar}
            grammar[f"<TOK_{token_id}>"] = [[start_nt]]
            print(pattern_grammar)
        
        with open(config.token_grammar_json, "w") as f:
            json.dump(grammar, f, indent=1)

        print(f"serialized token grammar to {config.token_grammar_json}")
        return d_token_to_samples

    def output_token_constraint(self, d_token_to_samples):
        tokens = sorted(d_token_to_samples.keys())
        with open("token_constraint.txt", "w") as f:
            f.write("\n".join(str(x) for x in tokens))
        print("output_token_constraint: wrote token_constraint.txt")

    def mine(self):
        self.generate_jsons()
        d_token_to_samples = self.mine_grammar()
        self.output_token_constraint(d_token_to_samples)


def main():
    print("Debug: Generating the grammar from existing jsons/")
    tm = TokenMiner("dummy", 10)
    tm.mine_grammar()

if __name__ == "__main__":
    main()
