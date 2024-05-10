# Reproducibility package for _Look Ma, No Input Samples! Mining Input Grammars from Code with Symbolic Parsing_

## Overview

This repository contains our prototype of the proposed approach, including a Dockerfile to reproduce results.

## Prerequisites

- x86 CPU (we used AMD Ryzen Threadripper 3960X 24-Core Processor)
- at least 64 GB RAM (we used 256 GB RAM)

## Grammar Format

We use the grammar format of https://www.fuzzingbook.org.

## Important Files

| File                                     | Description                             |
|------------------------------------------|-----------------------------------------|
| ./eval/eval.py                           | Main evaluation script                  |
| ./config.py                              | Central definition of parameters        |
| ./generalize/generalize.py               | Builds grammar from execution traces    |
| ./generalize/generalize_tokens.py        | Generalizes token instances to sets     |
| ./generalize/mine.py                     | Invokes KLEE on parse functions         |
| ./generalize/mine_tokens.py              | Invokes KLEE on tokenization function   |
| ./generalize/reduce_overapproximation.py | Reduces overapprox. in initial grammar  |

## Grammar artifacts

For a quick peek at the grammars produced by our prototype and the corresponding evaluation data, please refer to `./paper_evaluation_data/`.

## Running the Experiments

We provide a Dockerfile which
- installs all dependencies
- applies our changes and builds KLEE
- builds the evaluation subjects (calc, json, lisp, tinyc)
- runs our tool on each evaluation subject to produce the input grammars
- outputs evaluation results for each subject as .csv files
- accumulates evaluation results to a .tex table

Allow up to 24 hours for the experiments to finish.

The experiments can be run as follows:

```bash
sudo chmod -R 777 .
docker build . -t symbolic-grammar-mining
mkdir output
docker run -it -v $(pwd)/output:/staminag/data symbolic-grammar-mining
```

Results will be synced to `./output`.
