# STALAGMITE: Inferring Input Grammars from Code with Symbolic Parsing

STALAGMITE is a technique to mine _input grammars_ from recursive descent parsers.
In contrast to existing techniques, STALAGMITE does not require _sample inputs_.
Instead, STALAGMITE utilizes _symbolic execution_ to analyze parsers.
Input grammars have various applications, including fuzzing, debugging, documentation and reverse engineering.

## Prototype

This repository contains our STALAGMITE prototype, which is based on the [KLEE symbolic execution engine](https://github.com/klee/klee).

## Research paper

STALAGMITE is detailed and evaluated in our research paper, which is currently under submission to TOSEM.

## Reproducibility package

We provide a Dockerfile to reproduce our results.

### A quick peek at the grammar artifacts

If you just want to have a look at the grammars STALAGMITE mined from our evaluation subjects, see `paper_evaluation_data/`.

### Prerequisites

To build and run the docker container, we recommend the following minimum system specifications:

- **x86 CPU** (We used AMD Ryzen Threadripper 3960X 24-Core Processor)
- **Linux** (We used Ubuntu 22.04)
- **At least 16GB RAM per parallel experiment** (We used 256GB RAM)


### Important files


| File                                               | Description                             |
|----------------------------------------------------|-----------------------------------------|
| ./eval/eval.py                                     | Evaluation script                       |
| ./klee.patch                                       | KLEE changes                            |
| ./config.py                                        | Central definition of parameters        |
| ./system_level_grammar/traces_to_grammars.py       | Execution traces to grammar conversion  |
| ./system_level_grammar/generalize_tokens.py        | Token generalization                    |
| ./system_level_grammar/reduce_overapproximation.py | Overapproximation reduction             |
| ./subjects/                                        | Evaluation subjects                     |


### Running the experiments


The experiments can be run as follows:

```bash
make docker-build

make docker-run subject=tinyc
make docker-run subject=lisp
make docker-run subject=mjs
make docker-run subject=json
make docker-run subject=cjson
make docker-run subject=parson
make docker-run subject=calc
make docker-run subject=simplearithmeticparser
make docker-run subject=cgi_decode
```

Results will be copied to `./output_docker`.
For example,
- `./output_docker/subjects/cgi_decode/1/eval/` will contain `accuracy.csv` and `readability.csv`
- `./output_docker/subjects/cgi_decode/1/grammars/` will contain the mined grammars (initial and refined).


### Changing the limits

By default, all experiments are configured with a 16GB memory and 24h time limit.
To use different limits, e.g., a time limit of 4h and a memory limit of 8GB, create an environment file `config.env`:

```bash
MAX_TIME="240min"
MAX_MEMORY=8000
```

Now run an experiment with this config:

```bash
make docker-run-env subject=calc envfile=config.env
```