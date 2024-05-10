#!/usr/bin/env python

# This file was adapted from Mimid.

import sys
import json
import fuzzingbook.Parser as P
from fuzzingbook.GrammarFuzzer import display_tree
from common import is_nt, tree_to_str


def usage():
    print('''
parser.py <grammar> <input>
    An interface to the fuzzingbook parser. Returns if the given string can be parsed by the grammar.
            ''')
    sys.exit(0)

def main():
    args = sys.argv[1:]
    if not args or args[0] == '-h': usage()
    with open(args[0]) as f:
        grammar = json.load(f)
    start = "<start>"
    parser = P.IterativeEarleyParser(P.non_canonical(grammar), start_symbol=start)
    inp = args[1].encode().decode('unicode_escape') # so '\n' etc. is interpreted literally
    print("inp:")
    print(inp)
    print("bytes(inp):")
    print(inp.encode('utf-8'))


    try:
        result = parser.parse(inp)
        for tree in result:
            s = tree_to_str(tree)
            if s == inp:
                print('parsed')
                display_tree(tree).render(filename='parsetree')
                sys.exit(0)
            else:
                print('Invalid match %s' % repr(inp))
                sys.exit(1)
    except SyntaxError:
        print('Can not parse - syntax %s' % repr(inp))
        sys.exit(2)

if __name__ == '__main__':
    main()