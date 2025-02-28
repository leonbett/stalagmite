#ifndef COMMON_H
#define COMMON_H

#include "klee/klee.h"
#include <stdint.h>

extern uint32_t* tokens[100];
void __setup_tokens();
uint32_t stalagmite_get_token();
uint32_t stalagmite_get_token_by_id(uint32_t ID);
char* __setup_input_token_harness(int argc, char* argv[]);

#endif