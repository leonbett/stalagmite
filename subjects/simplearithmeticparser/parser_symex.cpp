// SimpleArithmeticParser
// https://github.com/SaturnMatt/SimpleArithmeticParser
//
// This project is a simple arithmetic expression parser that
// demonstrates recursive descent parsing techniques in C++.
//
// Released under the MIT License. For details, see the accompanying LICENSE file
// or visit https://opensource.org/licenses/MIT

// https://github.com/SaturnMatt/SimpleArithmeticParser/commit/43ca234b7a0b895ff56dc45e61a3279dc5f4c807

#include "parser.h"

#include <iostream>
#include "klee/klee.h"

Parser::Parser(const std::string& input) : input(input), pos(0) {}

// Main parsing function
int Parser::parse() {
    skip_whitespace();
    int result = parse_expression();
    skip_whitespace();
    if (pos < input.size()) {
        throw std::runtime_error("Unexpected character: " + std::string(1, input[pos]));
    }
    return result;
}

// Expression consisting of terms separated by '+' or '-'
int Parser::parse_expression() {
    int left = parse_term();
    skip_whitespace();
    while (pos < input.size() && (input[pos] == '+' || input[pos] == '-')) {
        char op = input[pos++];
        skip_whitespace();
        int right = parse_term();
        if (op == '+') left += right;
        else left -= right;
        skip_whitespace();
    }
    return left;
}

// Term consisting of factors separated by '*' or '/'
int Parser::parse_term() {
    int left = parse_factor();
    skip_whitespace();
    while (pos < input.size() && (input[pos] == '*' || input[pos] == '/')) {
        char op = input[pos++];
        skip_whitespace();
        int right = parse_factor();
        if (op == '*') left *= right;
        else left /= right;
        skip_whitespace();
    }
    return left;
}

// Factor is either an expression in parentheses or an integer
int Parser::parse_factor() {
    int value;
    skip_whitespace();
    if (input[pos] == '(') {
        pos++;
        skip_whitespace();
        value = parse_expression();
        skip_whitespace();
        if (input[pos] == ')') {
            pos++;  // Consume the closing parenthesis
        }
        else {
            throw std::runtime_error("Expected closing parenthesis");
        }
    }
    else if (std::isdigit(input[pos])) {
        value = parse_integer();
    }
    else {
        throw std::runtime_error("Unexpected character: " + std::string(1, input[pos]));
    }
    return value;
}

// Parse an integer
int Parser::parse_integer() {
    int value = 0;
    while (pos < input.size() && std::isdigit(input[pos])) {
        value = value * 10 + (input[pos++] - '0');
    }
    return value;
}

// Skip whitespace characters
void Parser::skip_whitespace() {
    while (pos < input.size() && std::isspace(input[pos])) {
        pos++;
    }
}

#include <string.h>

// no name mangling
extern "C" int kw_ep(int argc, char* argv[]) {
  int SYMEX_SIZE = atoi(argv[1]);
  char* inp = (char*)malloc(SYMEX_SIZE+1); 
  klee_make_symbolic(inp, SYMEX_SIZE+1, "input_str");
  klee_assume(inp[SYMEX_SIZE] == '\0');
  std::string input;
  for (int i = 0; i < strlen(inp); i++) {
    input += inp[i];
  }

    try {
        Parser parser(input);
        int evaluated_result = parser.parse();
        return 0;
    }
    catch (const std::runtime_error& e) {
        std::cerr << "Error: " << e.what() << std::endl;
        klee_silent_exit(1);
        return 1;
    }
}