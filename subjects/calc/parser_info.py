parser_functions = {
        "rdp.c": ["parse_expr", "parse_sum", "parse_mult", "parse_primary"]
}

parser_entry_point = ("rdp.c", "parse_expr")
assert parser_entry_point[1] in parser_functions[parser_entry_point[0]]