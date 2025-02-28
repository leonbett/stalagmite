MAX_TIME ?= "10min"

TOKEN_CURSOR ?= true
TOKENIZATION_FUNCTION ?= lex

GOLDEN_GRAMMAR ?= ../../data/golden_grammars/golden_grammar_lisp.json

ORIG_SRCS := parse_orig.c runtime.c
SRCS := parse_symex.c runtime.c ../__common__/common.c
LDFLAGS := -lgc

include ../common.mk