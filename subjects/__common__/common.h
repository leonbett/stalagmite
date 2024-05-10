#ifndef COMMON_H
#define COMMON_H

#include "klee/klee.h"
#include <stdint.h>

extern uint32_t* tokens[100];
void __setup_tokens();
void __oracle(int success);
uint32_t staminag_get_token();
char* __setup_input_token_harness(int argc, char* argv[]);
char* __setup_input_byte_cursor(int argc, char* argv[]);

#endif