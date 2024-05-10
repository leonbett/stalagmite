# This file was adapted from Mimid.

import random
import signal
import json
import argparse
import subprocess
from common import LimitFuzzer, put_can_parse

class TimeoutException(Exception):
    pass

def fuzz_alarm_handler(signum, frame):
    raise TimeoutException("Fuzzer timed out")

def _compute_precision(put, grammar, max_depth: int, count: int):
    fuzzer = LimitFuzzer(grammar)
    inputs = set()
    valid = []
    invalid = []
    while len(inputs) < count:
        signal.signal(signal.SIGALRM, fuzz_alarm_handler)
        signal.alarm(1)
        try:
            inp, _ = fuzzer.fuzz("<start>", max_depth=max_depth)
        except TimeoutException:
            print('Timeout in _compute_precision')
            continue
        finally:
            signal.alarm(0)

        if inp not in inputs:
            parsed = put_can_parse(put, inp)
            match parsed:
                case True:
                    valid.append(inp)
                case False:
                    invalid.append(inp)
                case None:
                    continue
                case _:
                    assert False, "unmatched"
            print(f"Inp ({len(inputs)}/{count} {repr(inp)} is valid=", parsed)
            inputs.add(inp)

    print("invalid: ", invalid)
    print("valid: ", valid)
    print(f"Precision ({len(valid)}/{len(valid)+len(invalid)})")
    precision = len(valid)/(len(valid)+len(invalid))
    assert count == len(valid)+len(invalid)
    return precision, valid

def compute_precision(put, grammar, max_depth: int, count: int) -> float:
    precision, _ = _compute_precision(put, grammar, max_depth, count)
    return precision

# This is used to compute coverage of valid inputs only.
def get_valid_inputs(put, grammar, max_depth: int, count: int) -> list[str]:
    _, valid = _compute_precision(put, grammar, max_depth, count)
    return valid

def run_inputs(put, inputs):
    for inp in inputs:
        p = subprocess.Popen(put, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        data, err = p.communicate(input=inp.encode('latin-1'))

"""
Maybe wrap f.fuzz in:
    try:
    except RecursionError:
        pass
"""
def main():
    parser = argparse.ArgumentParser(description='Input generation and precision generation script.')
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument('--fuzz', dest='fuzz', action='store_true', help='Generate (not necessarily distinct) inputs and output them on stdout.')
    mode_group.add_argument('--precision', dest='precision', action='store_true', help='Generate distinct inputs and calculate precision by feeding them to argv[1] of the supplied program.')
    parser.add_argument('--grammar', required=True, type=str, help='path to grammar')
    parser.add_argument('--count', required=True, type=int, help='count of inputs to be generated')
    parser.add_argument('--depth', required=True, type=int, help='maximum depth to be used by generation')
    parser.add_argument('--put', type=str, help='path to program under test (only required for precision measurement, should read input from stdin)')

    args = parser.parse_args()

    with open(args.grammar) as f:
        grammar = json.load(f)

    count = args.count
    max_depth = args.depth

    if args.fuzz:
        f = LimitFuzzer(grammar)
        i = 0
        while i < count:
            inp, _ = f.fuzz("<start>", max_depth=max_depth)
            print(repr(inp))
            i += 1
    else:
        assert args.precision
        compute_precision(args.put, grammar, max_depth, count)

if __name__ == '__main__':
    main()
