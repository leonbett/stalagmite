parser_functions = {
        "tiny.c": [
            "program",
            "statement",
            "term",
            "sum",
            "test",
            "expr",
            "paren_expr"
        ]
}

parser_entry_point = ("tiny.c", "program")
assert parser_entry_point[1] in parser_functions[parser_entry_point[0]]