set -e

NODE_ENV=production
swift package clean
gcc -o main-gmp.out -O2 -mtune=skylake -Wall -Wextra -Wwrite-strings -Wno-parentheses -Wpedantic -Warray-bounds -Wconversion main-gmp.c -Lgmp/.libs -lgmp

BATCH_SIZE=10
REPEAT_EVERYTHING_COUNT=1

i=0
while [ "$i" -lt "$REPEAT_EVERYTHING_COUNT" ]; do
  swift run --configuration release -Xswiftc -gnone -Xswiftc -O Main "$BATCH_SIZE"
  node main.js "$BATCH_SIZE"
  python3 -OO main.py "$BATCH_SIZE"
  ./main-gmp.out "$BATCH_SIZE"
  i=$((i + 1))
done
