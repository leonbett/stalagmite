#include "common.h"

extern int sym;
extern char** cursor;
void next_sym();

// tokenization proxy function (2 lines)
void sym_next_sym() {
  sym = staminag_get_token(); }

// token analysis
int kw_next_sym(int argc, char* argv[]) {
  char* inp = __setup_input_token_harness(argc, argv);

  // 4 unique lines
  cursor = &inp;
  klee_mark_cursor(cursor, sizeof(cursor));
  next_sym();
  klee_pass_token(klee_get_valuel(sym));
  
  return 0; // generic
}