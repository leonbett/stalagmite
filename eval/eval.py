import os
import argparse
import importlib
import sys
import json
import random
import shutil
from reduce_overapproximation import GrammarRefiner

from precision import compute_precision, get_valid_inputs, run_inputs
from recall import compute_recall
from readability import get_grammar_stats
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

def mine(subject: Subject):
    old_wd, old_path = prologue(subject)

    print('[-] Cleaning')
    os.system("make clean")
    os.system("make")
    os.system("echo event,seconds,formatted > timestamps")
    os.system("make mine")
    os.system("make convert-simplify-coarse")
    assert os.path.exists("initial_grammar.json"), "initial grammar mining failed"
    os.system(f"cp initial_grammar.json {subject.initial_grammar}")
    if os.path.exists("tokengrammar.json"):
        os.system(f"cp tokengrammar.json {subject.run_dir}")
    os.system(f"cp scc.json {subject.run_dir}")
    os.system(f"cp -r reads/ {subject.run_dir}")
    os.system(f"cp makefile.variables {subject.run_dir}")
    os.system(f"cp klee_commit_hash {subject.run_dir}")
    os.system(f"cp klee_examples_commit_hash {subject.run_dir}")

    epilogue(old_wd, old_path)

"""
    Reduce overapproximation in the mined grammar.
"""
def refine(subject: Subject):
    old_wd, old_path = prologue(subject)

    print('[-] Reducing overapproximation')
    os.system('echo start_refinement,$(date +%s),$(date +"%Y-%m-%d %H:%M:%S") >> timestamps')
    gf = GrammarRefiner(subject.initial_grammar, subject.put, subject.refined_grammar)
    gf.refine_grammar()
    os.system('echo end_refinement,$(date +%s),$(date +"%Y-%m-%d %H:%M:%S") >> timestamps')
    assert os.path.exists(subject.refined_grammar), "refined grammar was not generated"
    os.system(f"cp refined_grammar*.json {subject.run_grammar_dir}")

    epilogue(old_wd, old_path)


def copy_timestamps(subject: Subject):
    old_wd, old_path = prologue(subject)

    print('[-] Copying timestamps...')
    os.system(f"cp timestamps {subject.timestamps_file}")

    epilogue(old_wd, old_path)

"""
    Compute accuracy and output as csv.
"""
def data_accuracy(subject: Subject):
    old_wd, old_path = prologue(subject)

    with open(subject.golden_grammar) as f:
        golden_grammar = json.load(f)
    with open(subject.initial_grammar) as f:
        initial_grammar = json.load(f)
    with open(subject.refined_grammar) as f:
        refined_grammar = json.load(f)
    
    with open(subject.accuracy_csv_file, "w") as f:
        f.write("approach")
        for max_depth in config.max_depths:
            f.write(f",precision depth {max_depth}")
        for max_depth in config.max_depths:
            f.write(f",recall depth {max_depth}")
        for max_depth in config.max_depths:
            f.write(f",F1 depth {max_depth}")
        f.write("\n")

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

        with open(subject.accuracy_csv_file, "a") as f:
            f.write(label)
            for prec in precisions:
                f.write(f",{prec}")
            for rec in recalls:
                f.write(f",{rec}")
            for f1 in f1s:
                f.write(f",{f1}")
            f.write("\n")

    print(f"serialized {subject.accuracy_csv_file}")

    epilogue(old_wd, old_path)


"""
    Output grammar readability stats as a csv.
"""
def data_readability(subject: Subject):
    with open(subject.initial_grammar) as f:
        initial_grammar = json.load(f)
    with open(subject.refined_grammar) as f:
        refined_grammar = json.load(f)
    with open(subject.golden_grammar) as f:
        golden_grammar = json.load(f)

    initial_count_keys, initial_count_rules, initial_average_rule_length, initial_sum_rule_lengths = get_grammar_stats(initial_grammar, "<start>", [])
    refined_count_keys, refined_count_rules, refined_average_rule_length, refined_sum_rule_lengths = get_grammar_stats(refined_grammar, "<start>", [])
    golden_count_keys, golden_count_rules, golden_average_rule_length, golden_sum_rule_lengths = get_grammar_stats(golden_grammar, "<start>", [])


    with open(subject.readability_csv_file, "w") as f:
        f.write("approach,nonterminals,rule alternatives,average rule length,sum rule lengths\n")
        f.write(f"initial,{initial_count_keys},{initial_count_rules},{initial_average_rule_length},{initial_sum_rule_lengths}\n")
        f.write(f"refined,{refined_count_keys},{refined_count_rules},{refined_average_rule_length},{refined_sum_rule_lengths}\n")
        f.write(f"golden,{golden_count_keys},{golden_count_rules},{golden_average_rule_length},{golden_sum_rule_lengths}\n")

        print(f"serialized {subject.readability_csv_file}")


def data(subject: Subject):
    data_accuracy(subject)
    data_readability(subject)

def main():
    random.seed(0)

    parser = argparse.ArgumentParser(description='Main Eval Script')
    parser.add_argument('--subject', required=True, type=str, help='name of the current subject')

    group = parser.add_mutually_exclusive_group(required=True)

    group.add_argument('--mine', action='store_true', help='mines the grammar.')
    group.add_argument('--refine', action='store_true',help='reduces overapproximation. requirement: grammars were already mined via --mine')
    group.add_argument('--data', action='store_true', help='generates precision/recall table + readability table. requirement: (refined) grammars were already mined via --refine')
    group.add_argument('--all', action='store_true', help="mine+refine+data")

    args = parser.parse_args()
    if args.all:
        args.mine = args.refine = args.data = True

    assert os.path.exists(os.path.join(config.root, f'subjects/{args.subject}')), "subject does not exist"
    subject = Subject(args.subject)
    print("Processing subject=", subject.subject)

    if args.mine:
        mine(subject)
    if args.refine :
        refine(subject)
    if args.data:
        data(subject)

    copy_timestamps(subject)


if __name__ == "__main__":
    main()