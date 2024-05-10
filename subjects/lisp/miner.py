import config

from mine import Miner

class LispMiner(Miner):
    def get_name(self):
        return "lisp"
    
    @staticmethod
    def generate_parse_proxy_functions_c():
        ppfsc = []
        ppfsc.append('#include "klee/klee.h"')
        ppfsc.append('#include "parse.h"')
        ppfsc.append('')

        ppfsc.append('__attribute__((used))')
        ppfsc.append('struct sexp sym_parse_sexp(struct p_state *state) {')
        ppfsc.append('  struct sexp new_sexp;')
        ppfsc.append('  struct token tok = eat_tok(state);') # this calls GetNextToken once
        ppfsc.append('  return (struct sexp){};')
        ppfsc.append('}')
        ppfsc.append('')

        ppfsc.append('__attribute__((used))')
        ppfsc.append('struct sexp *sym_parse(struct p_state *state) {')
        ppfsc.append('  struct token tok = eat_tok(state);')
        ppfsc.append('  return NULL;')
        ppfsc.append('}')
        ppfsc.append('')

        for i in range(len(ppfsc)):
            ppfsc[i] += "\n"

        with open(config.proxy_parse_functions_c, "w") as f:
            f.writelines(ppfsc)
        
        print(f"serialized {config.proxy_parse_functions_c}")

    # used by harness
    def resolve_arg(self, arg_type: str, defined_ints: list):
        if arg_type == "%struct.p_state*":
            return "&state"
        else:
            assert False, "unhandled argument type"

    # => 5 unique LOC
    def get_harness_template(self):
        return '''
            #include "common.h"
            #include "parse.h"

            int kw_{fua}(int argc, char* argv[]) {{
                // generic token cursor setup
                __setup_tokens(); 

                // setup
                struct p_state state;
                klee_mark_cursor(&(state.tok), sizeof(state.tok));
                state.file = NULL;
                state.tok = lex(&state); // <=> initial GetNextToken;

                {fua}({args});

                // no oracle required: the function will abort on error.
                return 0;
            }}'''

def get_miner():
    return LispMiner(is_token_cursor = True,
                    tokenization_function="lex")

def main():
    miner = get_miner()
    miner.process_args()

if __name__ == "__main__":
    main()