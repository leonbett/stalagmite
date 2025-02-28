// source https://github.com/mystor/simple-lisp-parser-in-c/

#include<stdio.h>
#include<stdlib.h>
#include<string.h>
#include<assert.h>
#include "parse.h"

struct chr_lst {
    char *chrs;
    int capacity;
    int len;
};

struct chr_lst new_chr_lst() {
    struct chr_lst a_list = {
        malloc(4 * sizeof(char)),
        4,
        0
    };

    return a_list;
}

// BUG1: append_chr_lst has a bug which I fixed below.
/*
void append_chr_lst(struct chr_lst *lst, char chr) {
    if (lst->capacity >= lst->len) {
        lst->capacity *= 2;
        lst->chrs = realloc(lst->chrs, lst->capacity * sizeof(char));
    }
    lst->chrs[lst->len++] = chr;
}
*/
// Fixed
void append_chr_lst(struct chr_lst *lst, char chr) {
    if (lst->len >= lst->capacity) {
        lst->capacity *= 2;
        lst->chrs = realloc(lst->chrs, lst->capacity * sizeof(char));
    }
    lst->chrs[lst->len++] = chr;
}


/* Lexing = String -> Tokens */

struct token lex(struct p_state *state);

struct p_state new_p_state(FILE *file) {
    struct p_state state;
    state.file = file;

    // Lex the first token into the buffer
    state.tok = lex(&state);

    return state;
}

// Adapted lex function to read from input instead of FILE*.
#define EOF 0

char** g_cursor = NULL;
int my_getc(FILE* f) {
    char** cursor = (char**) f;
    if (g_cursor == NULL) {
        g_cursor = cursor;
    }
    int c = (char)**g_cursor;
    (*g_cursor)++;
    return c;
}

int my_ungetc(int c, FILE* f) {
  (*g_cursor)--;
  **g_cursor = c;
  return c;
}

struct token lex(struct p_state *state) {
    struct token tok;

    for (;;) {
        int chr = my_getc(state->file);

        switch (chr) {
        case EOF:
            tok.type = EOF_TOK;
            return tok;
        case '(':
            tok.type = LPAREN_TOK;
            return tok;
        case ')':
            tok.type = RPAREN_TOK;
            return tok;
        }

        // Parse a integer
        if ('0' <= chr && chr <= '9') {
            // Create the token
            tok.type = INT_TOK;
            tok.integer = chr - '0';

            // Read in the integer
            chr = my_getc(state->file);
            while ('0' <= chr && chr <= '9') {
                tok.integer *= 10;
                tok.integer += chr - '0';

                chr = my_getc(state->file);
            }

            my_ungetc(chr, state->file);

            return tok;
        }

        // Parse a symbol
        if (chr != ' ' && chr != '\n') {
            // Read in the characters into the list
            struct chr_lst symb = new_chr_lst();

            // BUG2: I fixed the loop condition below because it is buggy.
            // If getc returns EOF, it will be stuck in an infinite loop, appending "EOF" bytes.
            // Hence, it should stop at EOF.

            // while (chr != ' ' && chr != '\n' && chr != '(' && chr != ')') {
            while (chr != EOF && chr != ' ' && chr != '\n' && chr != '(' && chr != ')') {
                append_chr_lst(&symb, chr);

                chr = my_getc(state->file);
            }

            // Put the character back
            my_ungetc(chr, state->file);

            append_chr_lst(&symb, '\0');

            // Create the token
            tok.type = SYMBOL_TOK;
            tok.symbol = symb.chrs;
            return tok;
        }

        // If we read anything else, skip it
    }
}

struct token peek_tok(struct p_state *state) {
    return state->tok;
}

struct token eat_tok(struct p_state *state) {
    struct token tok = state->tok;
    state->tok = lex(state);
    return tok;
}


/* Parsing = Tokens -> AST (Abstract Syntax Tree) */

struct sexp parse_sexp(struct p_state *state) {
    struct sexp new_sexp;

    struct token tok = eat_tok(state);

    switch (tok.type) {
    case LPAREN_TOK:
        new_sexp.type = LIST;

        // Read in sexps to create a list
        int len = 0;
        int capacity = 4;
        struct sexp *list = malloc(sizeof(struct sexp) * capacity);

        while (peek_tok(state).type != RPAREN_TOK) { // Stop when we reach an RPAREN
            if (peek_tok(state).type == EOF_TOK) exit(1); // Avoid memory corruption
            if (len == capacity) {
                capacity *= 2;
                list = realloc(list, sizeof(struct sexp) * capacity);
            }
            list[len++] = parse_sexp(state);
        }

        eat_tok(state);

        if (len == capacity) {
            capacity *= 2;
            list = realloc(list, sizeof(struct sexp) * capacity);
        }
        list[len].type = END_OF_LIST;

        new_sexp.list = list;

        return new_sexp;
    case INT_TOK:
        new_sexp.type = INTEGER;
        new_sexp.integer = tok.integer;

        return new_sexp;
    case SYMBOL_TOK:
        new_sexp.type = SYMBOL;
        new_sexp.symbol = tok.symbol;

        return new_sexp;
    default:
        printf("Invalid start of sexp token: %d\n", tok.type);
        exit(1);
        // assert(0 && "Invalid start of sexp token!");
    }
}

/*
A program is a list of s-expressions. s-expressions are (lists of elements) or symbols or numbers

parse(tokens) parses an entire program by parsing sexp until it reaches a NULL
*/
struct sexp *parse(struct p_state *state) {
    int len = 0;
    int capacity = 4;
    struct sexp *list = malloc(sizeof(struct sexp) * capacity);

    while (peek_tok(state).type != EOF_TOK) {
        if (len == capacity) {
            capacity *= 2;
            list = realloc(list, sizeof(struct sexp) * capacity);
        }
        list[len++] = parse_sexp(state);
    }

    if (len == capacity) {
        capacity *= 2;
        list = realloc(list, sizeof(struct sexp) * capacity);
    }
    list[len].type = END_OF_LIST;

    return list;
}

void print_ast_node(struct sexp ast_node) {
    switch (ast_node.type) {
    case INTEGER:
        printf("INTEGER(%lld)", ast_node.integer);
        break;
    case SYMBOL:
        printf("SYMBOL(%s)", ast_node.symbol);
        break;
    case LIST:
        printf("LIST(\n");
        struct sexp *list = ast_node.list;
        while (list->type != END_OF_LIST) {
            print_ast_node(*list);
            printf(",");
            list++;
        }
        printf("\n)");
        break;
    case END_OF_LIST:
        printf("**EOL**\n");
        break;
    }
}
