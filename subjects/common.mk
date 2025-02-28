.PHONY: output-variables all orig symex combined.bc pre-mine mine clean clean-all clean-grammars clean-logs precision recall convert-% convert-simplify-%

SHELL := /bin/bash
GCC := gcc
CC := clang
CXX := clang++
LLVM_LINK := llvm-link
CFLAGS_SYMEX := -I ../klee/include -I ../__common__ -emit-llvm -c -g -O0 -Xclang -disable-O0-optnone
CXXFLAGS_SYMEX := -I ../klee/include -I ../__common__ -emit-llvm -c -g -O0 -Xclang -disable-O0-optnone -nostdinc++ -std=c++11 -I"../../klee-libcxx/libc++-install-110/include/c++/v1/"

# Default configuration
MAX_LEN ?= 50
MAX_TIME ?= "1440min"
MAX_MEMORY ?= 16000
TOKEN_CURSOR ?= false
RECURSION_LIMIT ?= 3
LOOP_LIMIT ?= 4
ONLY_LIMIT_SYNTAX_LOOPS ?= false
DEEP_INPUT_ACCESS_TRACKING ?= false
SWITCH_TYPE ?= simple
SEARCH_STRATEGY ?= bfs
SCC ?=
KLEEFLAGS ?=

# Quick check precision / recall
GRAMMARFILE ?= initial_grammar.json
DEPTH ?= 10
INPUT_COUNT ?= 100

OBJS := $(SRCS:.c=.bc)
OBJS := $(OBJS:.cpp=.bc)

all: orig symex
orig: a.out
symex: combined.bc

a.out: $(ORIG_SRCS)
	$(GCC) $^ -o $@ $(LDFLAGS)

%.bc: %.c
	$(CC) $(CFLAGS_SYMEX) $< -o $@

%.bc: %.cpp
	$(CXX) $(CXXFLAGS_SYMEX) $< -o $@

combined.bc: $(OBJS)
	$(LLVM_LINK) -o $@ $^

ifeq ($(TOKEN_CURSOR),true)
pre-mine: tokens
	@echo "Mining tokens first"

TOKEN_CURSOR_FLAG := --token-cursor
TOKEN_GRAMMAR_FILE := --token-grammar=tokengrammar.json
else	
pre-mine:
	@echo "Not mining tokens"

TOKEN_CURSOR_FLAG :=
TOKEN_GRAMMAR_FILE :=
endif

output-commit-hashes:
	echo "NOTFOUND" > klee_commit_hash
	echo "NOTFOUND" > klee_examples_commit_hash
	@if [ -f /stalagmite/klee.patch ]; then \
		head -n1 /stalagmite/klee.patch > klee_commit_hash; \
		cp /stalagmite/klee-examples.commit klee_examples_commit_hash; \
	fi

output-variables:
	( :; $(foreach v,                                       \
			$(filter-out $(VARS_OLD) VARS_OLD,$(.VARIABLES)), \
			echo '$(v) = $($(v))'; ) ) >  makefile.variables

mine: output-commit-hashes output-variables pre-mine
	echo "start_parser_symex,$$(date +%s),$$(date +"%Y-%m-%d %H:%M:%S")" >> timestamps
	klee $(KLEEFLAGS) --switch-type=$(SWITCH_TYPE) --output-module --libc=uclibc --posix-runtime --recursion-limit=$(RECURSION_LIMIT) --loop-limit=$(LOOP_LIMIT) --deep-input-access-tracking=$(DEEP_INPUT_ACCESS_TRACKING) --only-limit-syntax-loops=$(ONLY_LIMIT_SYNTAX_LOOPS) --only-output-states-covering-new --search=$(SEARCH_STRATEGY) --is-token-cursor=$(TOKEN_CURSOR) --max-time=$(MAX_TIME) --max-memory=$(MAX_MEMORY) --entry-point=kw_ep combined.bc $(MAX_LEN)
	echo "end_parser_symex,$$(date +%s),$$(date +"%Y-%m-%d %H:%M:%S")" >> timestamps

tokens-jsons:
	echo "start_token_mining,$$(date +%s),$$(date +"%Y-%m-%d %H:%M:%S")" >> timestamps
	rm -rf reads-letters/ reads-digits/ reads-punctuation/ reads-none/
	mkdir reads-letters reads-digits reads-punctuation reads-none
	klee $(KLEEFLAGS) --output-module --libc=uclibc --posix-runtime --is-token-exploration=true --trace-output-directory=reads-letters/ --max-memory-inhibit=false --max-memory=32000 --max-time=30min --entry-point=kw_$(TOKENIZATION_FUNCTION) --search=bfs combined.bc 10 letters
	klee $(KLEEFLAGS) --output-module --libc=uclibc --posix-runtime --is-token-exploration=true --trace-output-directory=reads-digits/ --max-memory-inhibit=false --max-memory=32000 --max-time=30min --entry-point=kw_$(TOKENIZATION_FUNCTION) --search=bfs combined.bc 10 digits
	klee $(KLEEFLAGS) --output-module --libc=uclibc --posix-runtime --is-token-exploration=true --trace-output-directory=reads-punctuation/ --max-memory-inhibit=false --max-memory=32000 --max-time=30min --entry-point=kw_$(TOKENIZATION_FUNCTION) --search=bfs combined.bc 10 punctuation
	klee $(KLEEFLAGS) --output-module --libc=uclibc --posix-runtime --is-token-exploration=true --trace-output-directory=reads-none/ --max-memory-inhibit=false --max-memory=32000 --max-time=30min --entry-point=kw_$(TOKENIZATION_FUNCTION) --search=bfs combined.bc 10 none
	echo "end_token_mining,$$(date +%s),$$(date +"%Y-%m-%d %H:%M:%S")" >> timestamps

tokens: tokens-jsons
	echo "start_token_generalization,$$(date +%s),$$(date +"%Y-%m-%d %H:%M:%S")" >> timestamps
	python3 ../../system_level_grammar/mine_tokens.py
	echo "end_token_generalization,$$(date +%s),$$(date +"%Y-%m-%d %H:%M:%S")" >> timestamps

precision:
	python3 ../../eval/precision.py --precision --grammar $(GRAMMARFILE) --count $(INPUT_COUNT) --depth $(DEPTH) --put ./a.out

recall:
	python3 ../../eval/recall.py --goldengrammar $(GOLDEN_GRAMMAR) --minedgrammar $(GRAMMARFILE) --count $(INPUT_COUNT) --depth $(DEPTH) --put ./a.out

convert-%:
	echo "start_traces_to_grammar,$$(date +%s),$$(date +"%Y-%m-%d %H:%M:%S")" >> timestamps
	time python3 ../../system_level_grammar/traces_to_grammar.py reads/ --batch --ctx-$* $(SCC) $(TOKEN_CURSOR_FLAG) $(TOKEN_GRAMMAR_FILE)
	echo "end_traces_to_grammar,$$(date +%s),$$(date +"%Y-%m-%d %H:%M:%S")" >> timestamps

# "none", "coarse", "fine" are possible
convert-simplify-%:
	echo "start_traces_to_grammar,$$(date +%s),$$(date +"%Y-%m-%d %H:%M:%S")" >> timestamps
	time python3 ../../system_level_grammar/traces_to_grammar.py reads/ --batch --simplify --ctx-$* $(SCC) $(TOKEN_CURSOR_FLAG) $(TOKEN_GRAMMAR_FILE)
	echo "end_traces_to_grammar,$$(date +%s),$$(date +"%Y-%m-%d %H:%M:%S")" >> timestamps

clean:
	rm -f *.bc
	rm -f -r klee-out-*
	rm -f -r klee-last
	rm -f *.gcda coverage_* plot.pdf a.out cov* *.csv

	rm -f -r reads
	mkdir reads

	rm -f -r traces_last_read
	mkdir traces_last_read

	rm -f -r traces_ordered
	mkdir traces_ordered

clean-grammars:
	rm -f *grammar.json

clean-logs:
	rm -f *.log

clean-all: clean-grammars clean-logs clean