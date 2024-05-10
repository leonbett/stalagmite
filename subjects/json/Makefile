CC := clang
GCC := gcc # Play nice with gcov
LLVM_LINK := llvm-link
CFLAGS_COV := -fprofile-arcs -ftest-coverage
CFLAGS_SYMEX := -I ../klee/include -I ../__common__ -emit-llvm -c -g -O0 -Xclang -disable-O0-optnone

.PHONY: all orig symex combined.bc symex_wrapper.c clean deepclean all coverage-verbose coverage-csv coverage-html code-coverage precision recall

SRCS := symex_wrapper.c vector.c ../__common__/common.c
OBJS := $(SRCS:.c=.bc)

all: orig symex
orig: a.out cov
symex: combined.bc

a.out: json.c vector.c
	$(GCC) $^ -o $@

cov: json.c vector.c
	$(GCC) $(CFLAGS_COV) $^ -o $@

# Some parse functions have internal linkage.
symex_wrapper.c: json.c proxy_parse_functions.c harnesses.c
	echo '#include "json.c"' > symex_wrapper.c
	echo '#include "proxy_parse_functions.c"' >> symex_wrapper.c
	echo '#include "harnesses.c"' >> symex_wrapper.c

proxy_parse_functions.c:
	python3 -c 'import miner; miner.get_miner().generate_parse_proxy_functions_c()'

# Empty harness is sufficient to compile target,
# which is required to extract args for actual harness generation.
harnesses.c:
	touch harnesses.c

%.bc: %.c
	$(CC) $(CFLAGS_SYMEX) $< -o $@

combined.bc: $(OBJS)
	$(LLVM_LINK) -o $@ $^

precision:
	python3 ../../eval/precision.py --precision --grammar $(GRAMMARFILE) --count 1000 --depth $(d) --put ./a.out

recall:
	python3 ../../eval/recall.py --goldengrammar ../../data/paper/grammars/golden/golden_grammar_json.json --minedgrammar $(GRAMMARFILE) --count 1000 --depth $(d) --put ./a.out

code-coverage:
	python3 ../../eval/precision.py --precision --grammar $(GRAMMARFILE) --count 1000 --depth $(d) --put ./cov

coverage-html:
	gcovr --html --html-details -o coverage_report.html

coverage-csv:
	gcovr --csv --branches --exclude-unreachable-branches -o coverage_report.csv

coverage-verbose:
	gcovr --branches --exclude-unreachable-branches -o coverage_verbose.txt

# To be executed before analysing the subject
deepclean: clean
	rm -f -r kleelog*
	rm -f -r genlog*
	rm -f -r refine*
	rm -f -r grammar*
	rm -f -r jsons_*
	rm -f harnesses.c

# To be executed in between parser function analyses
# => Does not delete function grammars
# Only delete *.bc in local directory; not __common__/common.bc (reason: race condition when building multiple subjects in parallel)
clean:
	rm -f *.bc
	rm -f -r klee-out-*
	rm -f -r klee-last

	rm -f *.gcda coverage_* plot.pdf a.out cov* *.csv

	rm -f -r jsons
	mkdir jsons

