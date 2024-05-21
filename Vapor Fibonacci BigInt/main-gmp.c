#include <bits/time.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#include "gmp/gmp.h"

void fibonacci(mpz_ptr result, int n)
{
  if (n == 1)
  {
    mpz_set_si(result, 0);
    return;
  }

  mpz_t previous;
  mpz_init(previous);

  mpz_t current;
  mpz_init(current);
  mpz_set_si(current, 1);

  for (int i = 2; i <= n; i++)
  {
    mpz_t next;
    mpz_init(next);
    mpz_add(next, previous, current);

    mpz_swap(previous, current); // previous = current
    mpz_swap(current, next);     // current = next
    mpz_clear(next);             // next = old previous
  }

  mpz_clear(previous);
  mpz_set(result, current);
}

struct Result
{
  int count;
  double fib_duration;
  double print_duration;
};

double diff_seconds(struct timespec end, struct timespec start)
{
  double sec = (double)(end.tv_sec - start.tv_sec);
  double nano = (double)(end.tv_nsec - start.tv_nsec);
  return sec + nano / 1000000000.0;
}

int main(int argc, char **argv)
{
  int counts[] = {10000, 30000, 100000, 300000, 1000000};
  int counts_len = sizeof(counts) / sizeof(int);
  int repeat_count = atoi(argv[1]);
  struct Result results[1000];

  for (int i = 0; i < counts_len; i++)
  {
    int count = counts[i];

    for (int j = 0; j < repeat_count; j++)
    {
      mpz_t result;
      mpz_init(result);
      struct timespec start, mid, end;

      clock_gettime(CLOCK_PROCESS_CPUTIME_ID, &start);
      fibonacci(result, count);
      clock_gettime(CLOCK_PROCESS_CPUTIME_ID, &mid);
      mpz_out_str(stdout, 10, result);
      mpz_clear(result);
      clock_gettime(CLOCK_PROCESS_CPUTIME_ID, &end);

      int index = i * repeat_count + j;
      results[index].count = count;
      results[index].fib_duration = diff_seconds(mid, start);
      results[index].print_duration = diff_seconds(end, mid);
    }
  }

  FILE *file = fopen("results.txt", "a");
  fseek(file, 0, SEEK_END);

  for (int j = 0; j < counts_len * repeat_count; j++)
  {
    struct Result r = results[j];
    fprintf(file, "GMP,%d,%f,%f\n", r.count, r.fib_duration, r.print_duration);
  }

  fclose(file);
}
