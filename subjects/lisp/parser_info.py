parser_functions = {
        "parse.c": ["parse", "parse_sexp"]
}

parser_entry_point = ("parse.c", "parse")
assert parser_entry_point[1] in parser_functions[parser_entry_point[0]]