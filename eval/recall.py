# This file was adapted from Mimid.

import random
import json
import argparse
import fuzzingbook.Parser as P
import signal
from common import LimitFuzzer, put_can_parse, tree_to_str

def timeout_handler(signum, frame):
    print("Timeout reached! Operation took too long.")
    raise TimeoutError("Operation timed out")

def compute_recall(put, goldengrammar, minedgrammar, max_depth: int, count: int) -> float:
    f = LimitFuzzer(goldengrammar)
    inputs = set()
    while len(inputs) < count:
        inp, _ = f.fuzz('<start>', max_depth=max_depth)
        print("recall -- generated inp: ", inp)
        if inp not in inputs:
            if put_can_parse(put, inp) == True:
                inputs.add(inp)
                print("inputs: ", len(inputs))

    parser = P.IterativeEarleyParser(P.non_canonical(minedgrammar), start_symbol='<start>')
    valid = []
    invalid = []
    for inp in inputs:
        try:
            print("trying to parse: ", repr(inp), flush=True)
            #signal.alarm(3) # 3 seconds
            result = parser.parse(inp)
            parsed = False
            for tree in result:
                s = tree_to_str(tree)
                if s == inp:
                    print("parsed=True")
                    parsed = True
                    break
                else:
                    print('Invalid match %s' % repr(inp))
            #signal.alarm(0)
        except SyntaxError:
            print('Can not parse - syntax %s' % repr(inp))
        #except TimeoutError:
        #    print('timeout, skip parsing of: ', inp)
  
        if parsed:
            valid.append(inp)
        else:
            invalid.append(inp)

    print("invalid: ", invalid)
    print("valid: ", valid)
    print(f"Recall ({len(valid)}/{len(valid)+len(invalid)})")
    recall = len(valid)/(len(valid)+len(invalid))
    return recall

def main():
    signal.signal(signal.SIGALRM, timeout_handler)

    parser = argparse.ArgumentParser(description='Recall calculation script.')
    parser.add_argument('--goldengrammar', required=True, type=str, help='path to grammar')
    parser.add_argument('--minedgrammar', required=True, type=str, help='path to grammar')
    parser.add_argument('--count', required=True, type=int, help='count of inputs to be generated')
    parser.add_argument('--depth', required=True, type=int, help='maximum depth to be used by generation')
    parser.add_argument('--put', required=True, type=str, help='path to program under test (only required for precision measurement, should read input from stdin)')
    args = parser.parse_args()

    with open(args.goldengrammar) as f:
        goldengrammar = json.load(f)

    with open(args.minedgrammar) as f:
        minedgrammar = json.load(f)

    f = LimitFuzzer(goldengrammar)
    compute_recall(args.put, goldengrammar, minedgrammar, args.depth, args.count)


if __name__ == "__main__":
    main()