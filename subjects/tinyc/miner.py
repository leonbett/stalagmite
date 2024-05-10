import config

from mine import Miner
import parser_info

class TinyCMiner(Miner):
    def get_name(self):
        return "tinyc"
    
    @staticmethod
    def generate_parse_proxy_functions_c():
        ppfsc = []
        ppfsc.append('#include "klee/klee.h"')
        ppfsc.append('#include <stdlib.h>')
        ppfsc.append('')
        ppfsc.append('node* sym_node() {')
        ppfsc.append(' node* n = malloc(sizeof(node));')
        ppfsc.append(' klee_make_symbolic((void*)n, sizeof(node), "proxy node");')
        ppfsc.append(' return n;')
        ppfsc.append('}')
        ppfsc.append('')

        for parser_function in parser_info.parser_functions["tiny.c"]:
            ppfsc.append('__attribute__((used))') # make sure compiler does not delete the function because it is not called
            ppfsc.append(f'node* sym_{parser_function}() {{')
            ppfsc.append('  next_sym();')
            ppfsc.append('  return sym_node();')
            ppfsc.append('}')
            ppfsc.append('')

        for i in range(len(ppfsc)):
            ppfsc[i] += "\n"

        with open(config.proxy_parse_functions_c, "w") as f:
            f.writelines(ppfsc)
        
        print(f"serialized {config.proxy_parse_functions_c}")

    def resolve_arg(self, arg_type: str, defined_ints: list):
        assert False, "Not implemented because TinyC does not have args."

    # => 3 unique LOC
    def get_harness_template(self):
        return '''
            #include "common.h"

            int kw_{fua}(int argc, char* argv[]) {{
                // generic token cursor setup
                __setup_tokens();
                
                klee_mark_cursor(&sym, sizeof(sym));
                next_sym();

                {fua}({args});

                // no oracle required: tinyc calls exit(1) on syntax error
                return 0;
            }}'''

def get_miner():
    return TinyCMiner(is_token_cursor = True,
                    tokenization_function="next_sym")

def main():
    miner = get_miner()
    miner.process_args()

if __name__ == "__main__":
    main()