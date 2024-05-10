'''
Purpose: Find inputs accepted by the PUT but not in L(GoldenGrammar).
'''

import argparse
import os
import json

import fuzzingbook.Parser as P

import config
from subject import Subject
from precision import get_valid_inputs
from common import tree_to_str

def can_parse(parser: P.IterativeEarleyParser, inp: str):
    try:
        print("Golden grammar - trying to parse: ", repr(inp), flush=True)
        result = parser.parse(inp)
        for tree in result:
            return True
            #s = tree_to_str(tree)
            #if s == inp:
            #    print("parsed=True")
            #    return True
            #else:
            #    print('Invalid match %s' % repr(inp))
    except SyntaxError:
        print('Can not parse - syntax %s' % repr(inp))
        return False
    return False

# - Generate inputs and filter *passing* ones with PUT as oracle
# - Output the inputs which can not be parsed by GG

def main():
    parser = argparse.ArgumentParser(description='RQ4 Script')
    parser.add_argument('--subject', required=True, type=str, help='name of the current subject (for output file). use "all" for all.')
    args = parser.parse_args()
    
    subjects = config.subjects

    if args.subject != "all":
        assert os.path.exists(os.path.join(config.root, f'subjects/{args.subject}')), "subject does not exist"
        subjects = [args.subject]
    
    for s in subjects:
        subject = Subject(s)
        print("Processing subject=", subject.subject)
        with open(subject.refined_grammar) as f:
            refined_grammar = json.load(f)
        with open(subject.golden_grammar) as f:
            golden_grammar = json.load(f)

        max_depth = 10
        valid_inputs = get_valid_inputs(subject.put, refined_grammar, max_depth, config.cnt_inputs)

        true_negatives = []
        parser = P.IterativeEarleyParser(P.non_canonical(golden_grammar), start_symbol='<start>')
        for inp in valid_inputs:
            parsed = can_parse(parser, inp)
            if not parsed:
                true_negatives.append(inp)
        
        for i, inp in enumerate(true_negatives):
            print(f"TN{i}:")
            print(f"repr: {repr(inp)}")
            print(f"inp: {inp}")
        
        print(f"Found {len(true_negatives)} true negatives.")


if __name__ == "__main__":
    main()