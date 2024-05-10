#include "common.h"

#include "parse.h"
struct token lex(struct p_state *state);

// tokenization proxy function (5 lines)
struct token sym_lex(struct p_state *state) {
  struct token tok;
  tok.type = staminag_get_token();
  tok.symbol = "A";
  return tok; }

// token analysis
int kw_lex(int argc, char* argv[]) { 
  char* inp = __setup_input_token_harness(argc, argv);

  // 6 unique lines
  char** cursor = &inp;
  klee_mark_cursor(cursor, sizeof(cursor));
  struct p_state state;
  state.file = (FILE*)cursor;
  struct token tok = lex(&state); 
  klee_pass_token(klee_get_valuel(tok.type));
  
  return 0; // generic
}