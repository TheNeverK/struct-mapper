#include <stdio.h>
#include <stdlib.h>
#include <stdbool.h>
#include <string.h>

struct simple1 {
    int a;
    bool b;
    char c;
};

int main(void) {
    simple1 me = { .a = 4,
                  .b = true,
                  .c = 'c'};

    exit(EXIT_SUCCESS);
}