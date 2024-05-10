#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <fcntl.h>
#include <unistd.h>

#include "parser.h"

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
  int result;
  int ret = rdp_parse_expression(my_string, &result);
  return ret;
}
