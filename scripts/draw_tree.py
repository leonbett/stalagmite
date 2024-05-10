import sys
import json

from fuzzingbook.GrammarFuzzer import display_tree
from fuzzingbook.Parser import IterativeEarleyParser, non_canonical


def main():
    if len(sys.argv) != 3:
        print("Usage: python3 draw_tree.py <grammar.json> <input>")
        sys.exit(1)
    
    grammar_file = sys.argv[1]
    inp = bytes(sys.argv[2], "utf-8").decode('unicode_escape') # inteprret \n as a single char

    print("inp: ", inp)

    with open(grammar_file, 'r') as f:
        grammar = non_canonical(json.load(f))

    print("grammar:")
    print(json.dumps(grammar, indent=1))

    parser = IterativeEarleyParser(grammar)
    tree = next(parser.parse(inp))
    print("tree: ", tree)
    tree = tree[1][0]

    display_tree(tree).render(filename='trees/tree')

if __name__ == "__main__":
    main()
