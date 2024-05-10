#include<gc.h>
#include<assert.h>
#include<string.h>
#include "parse.h"

typedef struct scm scm;

struct cons_cell {
  scm *car;
  scm *cdr;
};

enum scm_type {
  SCM_CONS,
  SCM_INT,
  SCM_FN
};

struct scm {
  enum scm_type type;
  
  union {
    struct cons_cell cons;
    long long int integer;
    scm *(*fn)(scm*);
  };
};

scm *append(scm *to, scm *value) {
  if (to == NULL) {
    scm *new_cell = GC_malloc(sizeof(scm));
    new_cell->type = SCM_CONS;
    new_cell->cons.car = value;
    new_cell->cons.cdr = NULL;

    return new_cell;
  } else {
    assert(to->type == SCM_CONS);
    to->cons.cdr = append(to->cons.cdr, value);
    
    return to;
  }
}

scm *_plus_(scm* args) {
  scm *acc = GC_malloc(sizeof(scm));
  acc->type = SCM_INT;

  while (args != NULL) {
    assert(args->type == SCM_CONS);
    assert(args->cons.car->type == SCM_INT);

    acc->integer += args->cons.car->integer;

    args = args->cons.cdr;
  }

  return acc;
}

scm _plus_scm = {.type = SCM_FN, .fn = _plus_};

scm *run_lisp(struct sexp a_sexp) {
  switch (a_sexp.type) {
  case LIST:;
    // Get the first element (which should be a symbol representing a function) and evaluate it
    scm *callee = run_lisp(a_sexp.list[0]);
    assert(callee->type == SCM_FN);
    
    scm *args = NULL;
    struct sexp *remaining = a_sexp.list + 1;

    while (remaining->type != END_OF_LIST) {
      args = append(args, run_lisp(*remaining));
      remaining++;
    }
    
    return callee->fn(args);
  case SYMBOL:;
    char *name = a_sexp.symbol;
    if (strcmp(name, "+") == 0) {
      return &_plus_scm;
    }
    assert(0 && "Stuff ain't implemented yet!");
    break;
  case INTEGER:;
    scm *val = GC_malloc(sizeof(scm));
    val->type = SCM_INT;
    val->integer = a_sexp.integer;

    return val;
  default:
    assert(0 && "Whoops...");
  }
}

void print_scm(scm *val) {
  if (val == NULL) { printf("NULL"); return; }
  switch (val->type) {
  case SCM_CONS:
    printf("(");
    print_scm(val->cons.car);
    printf(" . ");
    print_scm(val->cons.cdr);
    printf(")");
    break;
  case SCM_INT:
    printf("%lld", val->integer);
    break;
  case SCM_FN:
    printf("FN(%p)", val->fn);
    break;
  }
}

/*
int main() {
  GC_INIT();
  // Create the input file.
  // Right now, this requires an actual file, but on non-mac os x
  // systems, there is a function fmemopen() which lets you open
  // an in-memory buffer as a file handle. There are shims for it on
  // mac os x, but its more complex than it needs to be
  FILE *input = fopen("example.lisp", "r");
  
  // Create the parser state object. This could probably be moved into parse()
  // but for now you need to do it seperately
  struct p_state state = new_p_state(input);
  
  // parse the lisp code into an ast
  struct sexp *parsed = parse(&state);
  
  // Display the resulting ast
  print_ast_node(parsed[0]);

  printf("\n********************\n");

  scm *res = run_lisp(parsed[0]);
  
  printf("RESULT: ");
  print_scm(res);
  printf("\n");
}
*/

#include <stdlib.h>
#include <unistd.h>
#include <fcntl.h>


int main(int argc, char *argv[]) {
  char my_string[10240];
  if (argc == 1) {
    int chars = read(fileno(stdin), my_string, 10240);
    if (!chars) {
      exit(1);
    }
    my_string[chars] = 0;
    /*char *v = fgets(my_string, 10240, stdin);
    if (!v) {
      exit(1);
    }*/
    /*strip_input(my_string);*/
  } else {
    int fd = open(argv[1], O_RDONLY);
    int chars = read(fd, my_string, 10240);
    if (!chars) {
      exit(3);
    }
    my_string[chars] = 0;
    /*chars = strip_input(my_string);
    if (!chars) {
      exit(4);
    }*/
    close(fd);
  }
  printf("val: <%s>\n", my_string);
  char* ptr = &my_string[0];
  char** cursor = &ptr;
  struct p_state state = new_p_state(cursor); 
  struct sexp *parsed = parse(&state);
  // parse aborts (with non-zero exit code) on parse error.
  return 0;
}