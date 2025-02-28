#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "klee/klee.h"

#define MAX_TOKEN_IDS 256
uint32_t* tokens[100];
void __setup_tokens() {
  // Set up 100 symbolic tokens.
  for (int i = 0; i < sizeof(tokens)/sizeof(tokens[0]); i++) {
    char szTok[100];
    szTok[0] = 0;
    sprintf(szTok, "tok_%d", i); 
    tokens[i] = malloc(sizeof(uint32_t));
    klee_make_symbolic((void*)tokens[i], sizeof(uint32_t), szTok);
  }
}

uint32_t stalagmite_get_token_by_id(uint32_t ID) {
  uint32_t t = *tokens[ID];
  return t;
}

uint32_t stalagmite_get_token() {
  uint32_t ID = klee_get_next_token_ctr();
  return stalagmite_get_token_by_id(ID);
}

//////////////////////////////////////////////
// Mining tokens from tokenization function //
//////////////////////////////////////////////

#define ws_constraint (inp[i] == ' ') |  (inp[i] >= 9 & inp[i] <= 13)
#define letters_constraint (inp[i] == '\0') | (inp[i] >= 'a' & inp[i] <= 'z') | (inp[i] >= 'A' & inp[i] <= 'Z')
#define digits_constraint (inp[i] == '\0') | (inp[i] >= '0' & inp[i] <= '0')
#define punctuation_constraint (inp[i] == '\0') | (inp[i] >= '!' & inp[i] <= '/') | (inp[i] >= ':' & inp[i] <= '@') | (inp[i] >= '[' & inp[i] <= '`') | (inp[i] >= '{' & inp[i] <= '~')

char* __setup_input_token_harness(int argc, char* argv[]) {
  if (argc != 3) { exit(1); } 

  int SYMEX_SIZE = atoi(argv[1]);
  char* restrictions = argv[2];
  char* inp = malloc(SYMEX_SIZE); 
  klee_make_symbolic(inp, SYMEX_SIZE, "input_str");
  if (0 == strcmp(restrictions, "letters")) {
    for (int i = 0; i < SYMEX_SIZE-1; i++) {
      if (i==0 || i==1) klee_assume(ws_constraint | letters_constraint);
      else klee_assume(letters_constraint);
    }
  } else if (0 == strcmp(restrictions, "digits")) {
    for (int i = 0; i < SYMEX_SIZE-1; i++) {
      if (i==0 || i==1) klee_assume(ws_constraint | digits_constraint);
      else klee_assume(digits_constraint);
    }
  } else if (0 == strcmp(restrictions, "punctuation")) {
    for (int i = 0; i < SYMEX_SIZE-1; i++) {
      if (i==0 || i==1) klee_assume(ws_constraint | punctuation_constraint);
      else klee_assume(punctuation_constraint);
    }
  } else if (0 == strcmp(restrictions, "none")) {
    // no restrictions
  } else {
    // unimplemented
    exit(2);
  }
  klee_assume(inp[SYMEX_SIZE - 1] == '\0');

  return inp;
}