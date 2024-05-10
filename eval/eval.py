import os
import argparse
import importlib
import sys
import json
import random
import reduce_overapproximation

from precision import compute_precision, get_valid_inputs, run_inputs
from recall import compute_recall
from subject import Subject

import config

def prologue(subject: Subject):
    wd = os.getcwd()
    path_copy = sys.path[:]
    os.chdir(subject.subject_dir)
    sys.path.append(os.getcwd())
    return wd, path_copy

def epilogue(old_wd, old_path):
    os.chdir(old_wd)
    sys.path = old_path

'''
    Statically mine the grammars and join them.
'''
def mine(subject: Subject):
    old_wd, old_path = prologue(subject)

    print('[-] Cleaning')
    os.system("make deepclean")
    os.system("make")

    miner = __import__("miner")
    importlib.reload(miner)
    print("[-] Running miner")
    miner = miner.get_miner()
    if miner.is_token_cursor:
        print("[-] Mining token grammar")
        miner.mine_token_grammar()
    else:
        print("[-] Not mining token grammar (byte cursor)")
    print("[-] Mining syntax grammars")
    miner.mine_syntax_grammars()
    print("[-] Joining grammars")
    miner.join_grammars()
    assert os.path.exists(subject.initial_grammar), "initial joined grammar was not generated"

    epilogue(old_wd, old_path)

"""
    Dynamically reduce overapproximation in mined grammar.
"""
def refine(subject: Subject):
    old_wd, old_path = prologue(subject)

    print('[-] Reducing overapproximation')
    reduce_overapproximation.refine(subject.subject, subject.initial_grammar, subject.put)
    assert os.path.exists(subject.refined_grammar), "refined grammar was not generated"

    epilogue(old_wd, old_path)

"""
    Compute accuracy and output as csv.
    Accumulated tex table can be generated using static_grammar_mining/eval/gen_tex_accuracy_table.py.
"""
def data_accuracy(subject: Subject):
    old_wd, old_path = prologue(subject)

    with open(subject.golden_grammar) as f:
        golden_grammar = json.load(f)
    with open(subject.initial_grammar) as f:
        initial_grammar = json.load(f)
    with open(subject.refined_grammar) as f:
        refined_grammar = json.load(f)
    
    output_csv_file = os.path.join(config.accuracy_csv_dir, f"accuracy_{subject.subject}.csv")

    with open(output_csv_file, "w") as f:
        f.write("approach")
        for max_depth in config.max_depths:
            f.write(f",precision depth {max_depth}")
        for max_depth in config.max_depths:
            f.write(f",recall depth {max_depth}")
        for max_depth in config.max_depths:
            f.write(f",F1 depth {max_depth}")
        f.write("\n")
        #f.write("approach,precision depth 10,precision depth 20,recall depth 10,recall depth 20,F1 depth 10,F1 depth 20\n")

    for label, grammar in [('initial', initial_grammar), ('refined', refined_grammar)]:
        precisions = []
        recalls = []
        f1s = []
        for max_depth in config.max_depths:
            print(f"Computing precision/recall for grammar={label} and max_depth={max_depth}")
            precision = compute_precision(subject.put, grammar, max_depth, config.cnt_inputs)
            precisions.append(precision)
            recall = compute_recall(subject.put, golden_grammar, grammar, max_depth, config.cnt_inputs)
            recalls.append(recall)
            f1 = 2*(precision*recall)/(precision+recall)
            f1s.append(f1)

        with open(output_csv_file, "a") as f:
            f.write(label)
            for prec in precisions:
                f.write(f",{prec}")
            for rec in recalls:
                f.write(f",{rec}")
            for f1 in f1s:
                f.write(f",{f1}")
            f.write("\n")
            #f.write(f"{label},{precisions[0]},{precisions[1]},{recalls[0]},{recalls[1]},{f1s[0]},{f1s[1]}\n")

    print(f"serialized {output_csv_file}")

    epilogue(old_wd, old_path)

def data(subject: Subject):
    data_accuracy(subject)

def main():
    random.seed(0)

    parser = argparse.ArgumentParser(description='Main Eval Script')
    parser.add_argument('--subject', required=True, type=str, help='name of the current subject (for output file). use "all" for all.')

    group = parser.add_mutually_exclusive_group(required=True)

    group.add_argument('--mine', action='store_true', help='mines the grammar.')
    group.add_argument('--refine', action='store_true',help='reduces overapproximation. requirement: grammars were already mined via --mine')
    group.add_argument('--data', action='store_true', help='generates precision/recall table. requirement: (refined) grammars were already mined via --refine')
    group.add_argument('--all', action='store_true', help="mine+refine+data")
    


    args = parser.parse_args()
    if args.all:
        args.mine = args.refine = args.data = True

    subjects = config.subjects

    if args.subject != "all":
        assert os.path.exists(os.path.join(config.root, f'subjects/{args.subject}')), "subject does not exist"
        subjects = [args.subject]
    
    for s in subjects:
        subject = Subject(s)
        print("Processing subject=", subject.subject)

        if args.mine:
            mine(subject)
        if args.refine :
            refine(subject)
        if args.data:
            data(subject)


if __name__ == "__main__":
    main()
