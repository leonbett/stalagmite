#ifndef _PARSER_H
#define _PARSER_H

extern int rdp_parse_expression(const char *exp, int *result);
extern int opp_parse_expression(const char *exp, int *result);

enum {
	ERR_NONE,
	ERR_TOK,		/* unknown token */
	ERR_EOL,		/* prematurate EOL */
	ERR_BRACE,		/* unbalanced braces */
	ERR_OP,			/* invalid operator */
};

#endif
