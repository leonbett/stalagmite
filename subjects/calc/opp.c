/* A simple operator-precedence parser */
#include <ctype.h>
#include <stdio.h>
#include <stdlib.h>
#include <setjmp.h>

#include "parser.h"

#define ARRAY_SIZE(x)	(sizeof(x)/sizeof(x[0]))

static int parse_expression(const char **pexp, jmp_buf *env, char end);

static int add_func(int a, int b)	{ return a + b; }
static int minus_func(int a, int b)	{ return a - b; }
static int mult_func(int a, int b)	{ return a * b; }
static int div_func(int a, int b)	{ return a / b; }

struct op {
	char token;
	int prio;		/* aka precedence */
	int (*func)(int, int);
};

static struct op operators[] = {
	{
		.token		= '+',
		.prio		= 0,
		.func		= add_func,
	}, {
		.token		= '-',
		.prio		= 0,
		.func		= minus_func,
	}, {
		.token		= '*',
		.prio		= 1,
		.func		= mult_func,
	}, {
		.token		= '/',
		.prio		= 1,
		.func		= div_func,
	},
};

struct parse_desc {
	int lhs;
	struct op *op;
	jmp_buf *env;
};

static void init_parse_desc(struct parse_desc *desc, jmp_buf *env)
{
	desc->lhs = 0;
	desc->op = &operators[0];
	desc->env = env;
}

static void parse_error(const char *exp, struct parse_desc *desc, int err)
{
	/*
	 * Here we could do some clean up by using desc->{lhs,rhs} for
	 * example.
	 */
	longjmp(*desc->env, err);
}

/* this doesn't move pexp */
static void parse_op(const char **pexp, struct parse_desc *desc)
{
	int i;

	for (i = 0; i < ARRAY_SIZE(operators); i++) {
		if (operators[i].token == **pexp) {
			desc->op = &operators[i];
			return;
		}
	}
	parse_error(*pexp, desc, ERR_OP);
}

static int parse_primary(const char **pexp, struct parse_desc *desc)
{
	const char *exp = *pexp;
	jmp_buf *env = desc->env;
	int ret = 0;

	while (isspace(exp[0]))
		exp++;

	switch (exp[0]) {
	case '0': case '1': case '2': case '3': case '4':
	case '5': case '6': case '7': case '8': case '9':
		ret = strtol(exp, (char **)&exp, 10);
		break;
	case '(':
		exp++;
		ret = parse_expression(&exp, env, ')');
		exp++;
		break;
	case '\0':
		parse_error(exp, desc, ERR_EOL);
		break;
	default:
		parse_error(exp, desc, ERR_TOK);
		break;
	}

	while (isspace(exp[0]))
		exp++;

	*pexp = exp;
	return ret;
}

static int parse_expr(const char **pexp, struct parse_desc *desc1, char expect)
{
	int rhs, min_prio = desc1->op->prio;

	while (**pexp != expect) {

		parse_op(pexp, desc1);
		if (desc1->op->prio < min_prio)
			break;

		*pexp += 1;
		rhs = parse_primary(pexp, desc1);

		while (**pexp != expect) {
			struct parse_desc desc2 =
				{ .lhs = rhs, .env = desc1->env };

			parse_op(pexp, &desc2);
			if (desc2.op->prio <= desc1->op->prio)
				break;

			rhs = parse_expr(pexp, &desc2, expect);
		}
		desc1->lhs = desc1->op->func(desc1->lhs, rhs);
	}
	return desc1->lhs;
}

static int parse_expression(const char **pexp, jmp_buf *env, char end)
{
	struct parse_desc desc;

	init_parse_desc(&desc, env);
	desc.lhs = parse_primary(pexp, &desc);
	return parse_expr(pexp, &desc, end);
}

int opp_parse_expression(const char *exp, int *result)
{
	jmp_buf env;
	int ret;

	ret = setjmp(env);
	if (ret == 0)
		*result = parse_expression(&exp, &env, '\0');
	return ret;
}
