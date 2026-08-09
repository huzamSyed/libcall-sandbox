#include <stdio.h>
#include <stdlib.h>

int main(int argc, char **argv)
{
    int *p = malloc(sizeof(int));

    if (p == NULL)
        return 1;

    *p = argc;
    printf("value = %d\n", *p);

    free(p);
    return 0;
}
