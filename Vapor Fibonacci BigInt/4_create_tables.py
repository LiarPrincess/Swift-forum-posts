from math import sqrt, isfinite
from dataclasses import dataclass
from collections import defaultdict

# Column order
IMPLEMENTATION_NAMES = (
    "Node",
    "Attaswift",
    # "Attaswift_inout",
    "Numberick",
    # "Numberick_inout",
    "Violet",
    # "Violet_inout",
    "GMP",
    "Python",
)
RESULTS_FILE_PATH = "results.txt"
OUTPUT_FILE_PATH = "results-tables.md"

# Color value green/red if the difference is greater than
COLOR_PERCENTAGE = 5.0
SHOW_RELATIVE_STANDARD_DEVIATION = False


@dataclass
class ImplementationCountKey:
    def __init__(self, name: str, count: int) -> None:
        self.name = name
        self.count = count

        hash_object = name + str(count)
        self._hash = hash(hash_object)

    # '__eq__' is defined by 'dataclass'

    def __hash__(self) -> int:
        return self._hash


@dataclass
class Values:
    sum: float
    average: float
    standard_deviation: float
    relative_standard_deviation: float
    values: list[float]

    def __init__(self, name: str, count: int, values: list[float]) -> None:
        min_value = min(values)
        max_value = max(values)

        self.sum = 0
        self.values = []

        # Reject min/max
        for v in values:
            if v != min_value and v != max_value:
                self.sum += v
                self.values.append(v)

        if not self.values:
            raise BaseException(f"Not enough values for: {name}, {count}.")

        self.average = self.sum / len(self.values)
        self.standard_deviation = 0

        for v in self.values:
            self.standard_deviation += pow(v - self.average, 2)

        self.standard_deviation /= len(self.values)
        self.standard_deviation = sqrt(self.standard_deviation)
        self.relative_standard_deviation = (
            0.0
            if self.average == 0.0
            else self.standard_deviation * 100.0 / self.average
        )


def cell_value(
    average: float,
    relative_standard_deviation: float,
    first: float | None,
) -> str:
    value = f"{average:.5}"

    if SHOW_RELATIVE_STANDARD_DEVIATION and isfinite(relative_standard_deviation):
        emoji = "⚠️" if relative_standard_deviation > 5.0 else ""
        value += f" [±{relative_standard_deviation:.3}%{emoji}]"

    if first is None:
        return value

    to_first = 0.0 if average == 0 else first / average
    green_color_threshold = 1.0 + COLOR_PERCENTAGE / 100.0
    red_color_threshold = 1.0 - COLOR_PERCENTAGE / 100.0
    value += f" ({to_first:.3}x)"

    return (
        f'<span style="color:#39a275">{value}</span>'
        if to_first > green_color_threshold
        else (
            f'<span style="color:#df1c44">{value}</span>'
            if to_first < red_color_threshold
            else value
        )
    )


def write_table(
    f,
    counts: list[int],
    key_to_values: defaultdict[ImplementationCountKey, list[float]],
):
    f.write("|Count")

    for name in IMPLEMENTATION_NAMES:
        f.write("|")
        f.write(name)

    f.write("|\n")
    f.write("|-----")

    for name in IMPLEMENTATION_NAMES:
        f.write("|")
        f.write("-" * len(name))

    f.write("|\n")

    for count in counts:
        f.write("|")
        f.write(str(count).rjust(8))

        first_average: float | None = None

        for name in IMPLEMENTATION_NAMES:
            key = ImplementationCountKey(name, count)

            if key not in key_to_values:
                f.write("|-")
                continue

            values_raw = key_to_values[key]
            values = Values(name, count, values_raw)

            s = cell_value(
                values.average,
                values.relative_standard_deviation,
                first_average,
            )

            f.write("|")
            f.write(s)

            if first_average is None:
                first_average = values.average

        f.write("\n")


def main():
    counts = set[int]()
    key_to_fib_durations = defaultdict[ImplementationCountKey, list[float]](list)
    key_to_print_durations = defaultdict[ImplementationCountKey, list[float]](list)

    with open(RESULTS_FILE_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()

            if line:
                split = line.split(",")
                name = split[0]
                count = int(split[1])
                fib_duration = float(split[2])
                print_duration = float(split[3])

                key = ImplementationCountKey(name, count)
                key_to_fib_durations[key].append(fib_duration)
                key_to_print_durations[key].append(print_duration)
                counts.add(count)

    counts = sorted(counts)

    with open(OUTPUT_FILE_PATH, "w", encoding="utf-8") as f:
        f.write("# Fibonacci\n\n")
        write_table(f, counts, key_to_fib_durations)
        f.write("\n")
        f.write("# Fibonacci - print\n\n")
        write_table(f, counts, key_to_print_durations)


if __name__ == "__main__":
    main()
