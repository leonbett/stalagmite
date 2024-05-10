parser_functions = {
        "json.c": ["json_parse", "json_parse_object", "json_parse_array", "json_parse_value"]
}

parser_entry_point = ("json.c", "json_parse")
assert parser_entry_point[1] in parser_functions[parser_entry_point[0]]