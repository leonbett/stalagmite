import json
import sys

def main():
    if len(sys.argv) != 3:
        print("Usage: convert_mimid_grammar.py <mimid_grammar.json> <output_grammar.json>")
        sys.exit(1)

    mimid_grammar_path = sys.argv[1]
    output_grammar_path = sys.argv[2]

    with open(mimid_grammar_path, "r") as f:
        mimid_grammar = json.load(f)
    start = mimid_grammar["[start]"]
    assert start == "<START>"
    # unpack
    mimid_grammar = mimid_grammar["[grammar]"]
    # <START> -> <start>
    mimid_grammar["<start>"] = mimid_grammar[start]
    del mimid_grammar[start]
    
    with open(output_grammar_path, "w") as f:
        json.dump(mimid_grammar, f, indent=1)
        
    print(f"Converted grammar serialized to {output_grammar_path}.")


if __name__ == "__main__":
    main()