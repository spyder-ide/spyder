#include <stdio.h>

int main()
{
  struct foo
  {
    int x;
    float y;
  };

  struct foo var;
  struct foo* pvar;
  pvar = &var;

  var.x = 5;
  (&var)->y = 14.3;
  printf("%i - %.02f\n", var.x, (&var)->y);
  pvar->x = 6;
  pvar->y = 22.4;
  printf("%i - %.02f\n", pvar->x, pvar->y);
  return 0;
}
