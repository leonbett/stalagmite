#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "klee/klee.h"

#define MAX_TOKEN_IDS 256
uint32_t* tokens[100];
void __setup_tokens() {
  // Read token values found by token exploration.
  FILE *file;
  int token_ids[MAX_TOKEN_IDS] = {0};
  int cnt = 0;
  char buffer[100];

  file = fopen("token_constraint.txt", "r");
  if (file == NULL) {
    printf("Error opening file.\n");
    assert(0);
  }
  while (fgets(buffer, sizeof(buffer), file) != NULL && cnt < MAX_TOKEN_IDS) {
    int num = atoi(buffer);
    token_ids[cnt++] = num;
  }   
  fclose(file);

  // Set up 100 symbolic tokens and constrain them to the token values.
  for (int i = 0; i < sizeof(tokens)/sizeof(tokens[0]); i++) {
    char szTok[100];
    szTok[0] = 0;
    sprintf(szTok, "tok_%d", i);
    tokens[i] = malloc(sizeof(uint32_t));
    klee_make_symbolic((void*)tokens[i], sizeof(uint32_t), szTok);
    int token_constraint = 0;
    for (int t = 0; t < cnt; t++) {
      token_constraint |= (*tokens[i] == token_ids[t]);
    }
    klee_assume(token_constraint);
  }
}

uint32_t staminag_get_token() {
  uint32_t ID = klee_get_next_token_ctr();
  uint32_t t = *tokens[ID];
  return t;
}

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

void __oracle(int success) {
  if (!success) klee_silent_exit(1);
}

char* __setup_input_byte_cursor(int argc, char* argv[]) {
  if (argc != 2) { exit(1); }
  int SYMEX_SIZE = atoi(argv[1]);
  char* inp = malloc(SYMEX_SIZE);
  klee_make_symbolic(inp, SYMEX_SIZE, "input_str");

  for (int i = 0; i < SYMEX_SIZE; i++) {
    klee_assume(inp[i] >= 0 & inp[i] < 127); // printable
  }

  klee_assume(inp[SYMEX_SIZE - 1] == '\0');
  return inp;
}