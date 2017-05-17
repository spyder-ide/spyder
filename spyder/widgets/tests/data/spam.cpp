#include<stdio.h>
#include<spam.h>

namespace eggs;

typedef struct spam {
   int sausage;
} spam;


int spam(*spam ptr)
{
    printf("spam\n");
}