import sys
import json
import fuzzingbook.Parser as P
from fuzzingbook.Grammars import is_valid_grammar

def main():
    grammarfile = sys.argv[1]
    with open(grammarfile, "r") as f:
        grammar = json.load(f)
    nc_grammar = P.non_canonical(grammar)
    assert is_valid_grammar(nc_grammar)

if __name__ == "__main__":
    main()