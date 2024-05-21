const fs = require("fs");

function fib_loop(n) {
  if (n <= 1) {
    return BigInt(n);
  } else {
    let a = BigInt(0);
    let b = BigInt(1);
    let temp;
    for (let i = 2; i <= n; i++) {
      temp = a + b;
      a = b;
      b = temp;
    }
    return b.toString();
  }
}

class Result {
  constructor(count, fibDuration, printDuration) {
    this.count = count;
    this.fibDuration = fibDuration;
    this.printDuration = printDuration;
  }
}

function diffSeconds(end, start) {
  return end[0] - start[0] + (end[1] - start[1]) / 1000000000.0;
}

const results = [];
const repeatCount = parseInt(process.argv[2]);

for (const count of [10000, 30000, 100000, 300000, 1000000]) {
  for (let i = 0; i < repeatCount; i++) {
    const start = process.hrtime();
    let f = fib_loop(count);
    const mid = process.hrtime();
    console.log(f);
    const end = process.hrtime();

    const fibDuration = diffSeconds(mid, start);
    const printDuration = diffSeconds(end, mid);
    const r = new Result(count, fibDuration, printDuration);
    results.push(r);
  }
}

if (!process.argv.includes("PERFORMANCE")) {
  for (const r of results) {
    fs.appendFileSync("results.txt", `Node,${r.count},${r.fibDuration},${r.printDuration}\n`);
  }
}
