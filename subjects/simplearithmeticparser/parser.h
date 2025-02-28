// SimpleArithmeticParser
// https://github.com/SaturnMatt/SimpleArithmeticParser
//
// This project is a simple arithmetic expression parser that
// demonstrates recursive descent parsing techniques in C++.
//
// Released under the MIT License. For details, see the accompanying LICENSE file
// or visit https://opensource.org/licenses/MIT

#ifndef PARSER_H
#define PARSER_H

#include <string>
#include <cctype>
#include <stdexcept>

class Parser {
public:
    Parser(const std::string& input);
    int parse();

private:
    std::string input;      // The input arithmetic expression
    size_t pos;             // The current position in the input string

    void skip_whitespace();
    int parse_expression();
    int parse_term();
    int parse_factor();
    int parse_integer();
};

#endif