import config
import re
from mine import Miner

class JSONMiner(Miner):
    def get_name(self):
        return "json"
    
    @staticmethod
    def generate_parse_proxy_functions_c():
        # Extract function signature
        re_function_header = r"(.+ (json_parse.+)\(.*\)\s*\{)"

        matches = []
        with open("json.c", "r") as f:
            for line in f:
                m = re.match(re_function_header, line)
                if m:
                    matches.append(m)

        ppfsc = []
        ppfsc.append('#include "json.h"')
        ppfsc.append('#include "klee/klee.h"')
        ppfsc.append('')
        for m in matches:
            function_signature_with_brace = m.group(1)
            function_name = m.group(2)
            ppfsc.append('__attribute__((used))') # make sure compiler does not delete the function because it is not called
            ppfsc.append(function_signature_with_brace.replace(function_name, f"sym_{function_name}"))
            ppfsc.append(f'  ++(*cursor);') # Now we increment byte-cursor like we do for token cursor
            ppfsc.append(f'  return klee_int("_{function_name}");') ## was: return 1, but I this is more general and should work too.
            ppfsc.append('}')
            ppfsc.append('')

        for i in range(len(ppfsc)):
            ppfsc[i] += "\n"

        with open(config.proxy_parse_functions_c, "w") as f:
            f.writelines(ppfsc)
        
        print(f"serialized {config.proxy_parse_functions_c}")

    def resolve_arg(self, arg_type: str, defined_ints: list):
        if arg_type == "i8**":
            return "cursor"
        elif arg_type == "i8*": # first arg of json_parse
            return "inp"
        elif arg_type == "%struct.json_value*":
            return "&result"
        elif arg_type == "i32": # not used
            new_var = f"int_arg_{len(defined_ints)}"
            defined_ints.append(new_var)
            return new_var
        else:
            assert False, "unhandled argument type"

    # => 3 unique LOC
    def get_harness_template(self):
        return '''
            #include "common.h"
            #include "json.h"
            int kw_{fua}(int argc, char* argv[]) {{
                // generic byte cursor setup
                char* inp = __setup_input_byte_cursor(argc, argv);

                // setup
                char** cursor = &inp;
                json_value result;

                // call parse function under analysis
                int success = {fua}({args});
            
                // generic parse oracle
                __oracle(success);

                return 0;
            }}'''
    
def get_miner():
    return JSONMiner(is_token_cursor = False)

def main():
    miner = get_miner()
    miner.process_args()

if __name__ == "__main__":
    main()