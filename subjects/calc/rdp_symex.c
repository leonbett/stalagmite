#include "klee/klee.h"

/* A simple recursive descent parser */
#include <ctype.h>
#include <stdio.h>
#include <stdlib.h>
#include <assert.h>

#include "parser.h"

#define ARRAY_SIZE(x)	(sizeof(x)/sizeof(x[0]))

static int parse_expr(const char **pexp, char expect, int *result);

static int parse_primary(const char **pexp, int *value)
{
	const char *exp = *pexp;
	int rv = 0;

	while (isspace(exp[0]))
		exp++;

	switch (exp[0]) {
	case '0': case '1': case '2': case '3': case '4':
	case '5': case '6': case '7': case '8': case '9':
		*value = strtol(exp, (char **)&exp, 10);
		break;
	case '(':
		exp++;
		rv = parse_expr(&exp, ')', value);
		exp++;
		break;
	case '\0':
		rv = ERR_EOL;
		goto out;
	default:
		rv = ERR_TOK;
		goto out;
	}

	while (isspace(exp[0]))
		exp++;
out:
	*pexp = exp;
	return rv;
}

static int parse_mult(const char **pexp, char expect, int *value)
{
	int rh, ret;

	ret = parse_primary(pexp, value);
	if (!ret)
		while (**pexp != expect) {
			char op = **pexp;

			if (op != '*' && op != '/')
				break;

			(*pexp)++;
			ret = parse_primary(pexp, &rh);
			if (ret)
				break;

			switch (op) {
			case '*':
				*value *= rh;
				break;
			case '/':
				*value /= rh;
				break;
			}
		}
	return ret;
}

static int parse_sum(const char **pexp, char expect, int *value)
{
	int rh, ret;

	ret = parse_mult(pexp, expect, value);
	if (!ret)
		while (**pexp != expect) {
			char op = **pexp;

			ret = ERR_TOK;
			if (op != '+' && op != '-')
				break;

			(*pexp)++;
			ret = parse_mult(pexp, expect, &rh);
			if (ret)
				break;

			switch (op) {
			case '+':
				*value += rh;
				break;
			case '-':
				*value -= rh;
				break;
			}
		}
	return ret;
}

static int parse_expr(const char **pexp, char expect, int *result)
{
	int err = parse_sum(pexp, expect, result);

	/*
	 * Adjust error code to make it a little bit more usefull.
	 */
	if (err == ERR_TOK && **pexp == '\0') {
		err = ERR_EOL;
		if (expect == ')')
			err = ERR_BRACE;
	}
	return err;
}

int rdp_parse_expression(const char *exp, int *result)
{
	return parse_expr(&exp, '\0', result);
}

int kw_ep(int argc, char* argv[]) {
	int SYMEX_SIZE = atoi(argv[1]);
	char* inp = malloc(SYMEX_SIZE+1); 
	klee_make_symbolic(inp, SYMEX_SIZE+1, "input_str");
	for (int i = 0; i < SYMEX_SIZE; i++) {{
		// Workaround for a bug in strtol.
		// KLEE finds that strtol can accept DIGITs or '`' (96d).
		// I couldn't verify this; I checked the uclibc implementation
		// of strtol, and it does not accept that character.
		// So I think it's a bug in Z3/KLEE.
		klee_assume(inp[i] != 96);
	}}
	klee_assume(inp[SYMEX_SIZE] == '\0');

	int result;
	int ret = rdp_parse_expression(inp, &result);
	if (ret) klee_silent_exit(1);
	return 0;
}