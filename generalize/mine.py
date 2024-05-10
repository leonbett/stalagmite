import sys
import glob
import os
import re
import subprocess
import argparse

import config

from parser_info import parser_functions, parser_entry_point

from generalize import generalize, inline_single_rules_and_opt_generalization
from generalize_helpers import load_json_file, is_nt, undefined_nts, find_reachable_keys, serialize_grammar, print_grammar, unreachable_nonterminals
from generalize_tokens import any_str

from mine_tokens import TokenMiner

class Miner():
    def get_name(self):
        assert False, "Implement me in subclass"

    def generate_parse_proxy_functions_c(self):
        assert False, "Implement me in subclass"

    def resolve_arg(self, arg_type: str, defined_ints: list):
        assert False, "Implement me in subclass"

    def get_harness_template(self):
        assert False, "Implement me in subclass"

    def run_klee(self, fua):
        command = ["klee",
                "--switch-type=simple",
                "--output-module",
                "--libc=uclibc",
                "--posix-runtime",
                f"--max-time={config.max_time_syntax}",
                "--static-grammar-mining",
                f"--llvm-pass-parser-function-under-analysis={fua}",
                f"--parser-function-under-analysis={fua}",
                f"--byte-cursor={str(not self.is_token_cursor).lower()}",
                f"--tokenization-function={self.tokenization_function if self.is_token_cursor else '__dummy__not__used__ff'}",
                f"--entry-point=kw_{fua}",
                "--search=bfs"]
        for parser_function in self.parser_functions:
            command.append(f"--parser-functions={parser_function}")
        command.extend(["combined.bc", f"{config.max_input_length}"])
        print("Running klee: ", command)
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return result

    def generate_harness(self, fua: str, args: list):
        # tuples of (typename, value)
        defined_ints = []
        arg_s = ', '.join(self.resolve_arg(arg_type, defined_ints) for arg_type in args)
        int_defs = []
        if defined_ints != []:
            for i, defined_int in enumerate(defined_ints):
                int_defs.append(f'int {defined_int} = klee_int("sym_{defined_int}");')
        int_def_s = "\n".join(int_defs)

        format_dict = {'fua': fua, 'args': arg_s, 'int_defs': int_def_s}
        harness = self.get_harness_template().format(**format_dict)
        return harness

    def extract_args(self, ll_fname):
        with open(ll_fname, "r") as f:
            bc = f.readlines()
        
        d = {}
        pattern = r"define .*@(.+)\((.*)\).*{"
        for line in bc:
            # match 1: function name
            # match 2: arguments
            m = re.match(pattern, line)
            if m:
                fname = m.group(1)
                s_args = m.group(2)
                if fname in self.parser_functions:
                    print(f'{fname}({s_args})')
                    assert fname not in d
                    args = s_args.split(',')
                    for i in range(len(args)):
                        args[i] = args[i][:args[i].rfind('%')].strip()
                    args = [a for a in args if a != ''] # return empty list of no args
                    d[fname] = args
        return d

    def generate_harnesses(self):
        os.system("make clean")
        os.system("make")
        # Generate combined.ll
        os.system("llvm-dis combined.bc")
        d_fname_to_args = self.extract_args("combined.ll")
        harnesses = []
        for fname, args in d_fname_to_args.items():
            harness = self.generate_harness(fname, args)
            harnesses.append(harness)

        with open("harnesses.c", "w") as f:
            for harness in harnesses:
                f.write(harness + "\n")

    def generate_function_grammar(self, fua):
        print("Processing: ", fua)
        self.generate_parse_proxy_functions_c()
        os.system("make clean")
        os.system("make")
        result = self.run_klee(fua)
        with open(f"kleelog_{fua}", "w") as f:
            f.write("This kleelog was produced using:\n")
            f.write(result.stderr + result.stdout)
        print("</KLEE>")
        os.system(f"cp -r jsons/ jsons_{fua}") # for backup, generalize reads jsons/
        isEntryPoint = fua == self.parser_entry_point
        called_ppfs: set = generalize(fua, self.is_token_cursor, isEntryPoint) # generates grammar

    def generate_all_function_grammars(self):
        for fua in self.parser_functions:
            self.generate_function_grammar(fua)

    def mine_syntax_grammars(self):
        self.generate_harnesses()
        self.generate_all_function_grammars()

    def mine_token_grammar(self):
        tm = TokenMiner(tokenization_function=self.tokenization_function)
        tm.mine()

    '''
        This function joins
            - all syntax function grammars
            - the token grammar, if `self.is_token_cursor`
    '''
    def join_grammars(self):
        # Join all "grammar*.json files"
        self.d_fua_id_to_grammar = {}
        pattern = "grammar*.json"
        grammar_files = glob.glob(pattern)
        for file_path in grammar_files:
            print(file_path)
            d = load_json_file(file_path)
            fua_id = file_path[len("grammar_"):-len(".json")]
            self.d_fua_id_to_grammar[fua_id] = d

        print_grammar("complete_deserialized_sub_grammars", self.d_fua_id_to_grammar)
        grammar = {}
        for fua_id in sorted(self.d_fua_id_to_grammar.keys()):
            grammar = {**grammar, **self.d_fua_id_to_grammar[fua_id]}
        grammar["<start>"] = [[f"<{self.parser_entry_point}>"]]

        if self.is_token_cursor:
            token_grammar = load_json_file(config.token_grammar_json)
            grammar = {**grammar, **token_grammar}

        print_grammar("joined_grammar", grammar)

        print("Undefined NTs after adding token grammar:")
        print(undefined_nts(grammar)) # debug print
        assert len(undefined_nts(grammar)) == 0

        # Defining undefined tokens with <any_str> here.
        # Actually, tokens are not undefined but defined as [[]] here (by function grammar def).
        for key in grammar:
            if key.startswith('<TOK_'):
                if grammar[key] == [[]]:
                    print(f"Dummy function-level token definition: grammar[{key}] = {grammar[key]}. Widening to <any_str>.")
                    grammar = {**grammar, **any_str}
                    grammar[key] = [["<any_str>"]]

        grammar = inline_single_rules_and_opt_generalization(grammar)
        for nt in unreachable_nonterminals(grammar, start_symbol='<start>'):
            del grammar[nt]

        serialize_grammar(grammar, "final_grammar.json")
        serialize_grammar(grammar, os.path.join(config.grammars_initial_dir, f"initial_grammar_{self.get_name()}.json"))

    def process_args(self):
        parser = argparse.ArgumentParser(description='Miner Argument Parser')
        parser.add_argument('--tokens', action='store_true', help='Mine token grammar?')
        parser.add_argument('--syntax', action='store_true', help='Mine syntax grammar?')
        parser.add_argument('--join', action='store_true', help='Join existing token and syntax grammar?')
        parser.add_argument('--all', action='store_true', help='(If is_token_cursor: Mine token grammar +) Mine syntax grammar + Join?')
        args = parser.parse_args()
        if args.all:
            if self.is_token_cursor:
                args.tokens = True
            args.syntax = True
            args.join = True
        if not (args.tokens or args.syntax or args.join):
            print("At least one argument must be provided!")
            parser.print_usage()
            sys.exit(1)
        if args.tokens:
            assert self.is_token_cursor
            self.mine_token_grammar()
        if args.syntax:
            self.mine_syntax_grammars()
        if args.join:
            self.join_grammars()

    def __init__(self, is_token_cursor: bool, tokenization_function: str = None):
        self.is_token_cursor = is_token_cursor
        self.tokenization_function = tokenization_function # only relevant if `is_token_cursor`

        self.parser_functions = [item for sublist in parser_functions.values() for item in sublist] # flatten, remove file name
        self.parser_entry_point = parser_entry_point[1] # remove file name

        self.d_fua_id_to_grammar = {}