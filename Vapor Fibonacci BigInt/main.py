import sys
from dataclasses import dataclass
from timeit import default_timer as timer

sys.set_int_max_str_digits(0)


def fibonacci(n: int) -> int:
    if n == 1:
        return 0

    previous = 0
    current = 1

    for _ in range(2, n + 1):
        next = previous + current
        previous = current
        current = next

    return current


@dataclass
class Result:
    count: int
    fib_duration: float
    print_duration: float


results = list[Result]()
repeat_count = int(sys.argv[1])

for count in (10000, 30000, 100000, 300000, 1000000):
    for _ in range(repeat_count):
        start = timer()
        f = fibonacci(count)
        mid = timer()
        print(f)
        end = timer()

        r = Result(count, mid - start, end - mid)
        results.append(r)


with open("results.txt", "a") as f:
    for r in results:
        f.write(f"Python,{r.count},{r.fib_duration},{r.print_duration}\n")
