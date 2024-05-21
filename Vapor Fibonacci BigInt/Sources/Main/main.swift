import Foundation
import Attaswift
import Violet
import Numberick

func attaswift(_ n: Int) -> Attaswift.BigInt {
  precondition(n > 0)

  if n == 1 {
    return 0
  }

  var previous: Attaswift.BigInt = 0
  var current: Attaswift.BigInt = 1

  for _ in 2 ... n {
    let next = previous + current
    previous = current
    current = next
  }

  return current
}

func attaswift_inout(_ n: Int) -> Attaswift.BigInt {
  precondition(n > 0)

  if n == 1 {
    return 0
  }

  var previous: Attaswift.BigInt = 0
  var current: Attaswift.BigInt = 1

  for _ in 2 ... n {
    previous += current
    swap(&previous, &current)
  }

  return current
}

func violet(_ n: Int) -> Violet.BigInt {
  precondition(n > 0)

  if n == 1 {
    return 0
  }

  var previous: Violet.BigInt = 0
  var current: Violet.BigInt = 1

  for _ in 2 ... n {
    let next = previous + current
    previous = current
    current = next
  }

  return current
}

func violet_inout(_ n: Int) -> Violet.BigInt {
  precondition(n > 0)

  if n == 1 {
    return 0
  }

  var previous: Violet.BigInt = 0
  var current: Violet.BigInt = 1

  for _ in 2 ... n {
    previous += current
    swap(&previous, &current)
  }

  return current
}

func numberick(_ n: Int) -> Numberick.UIntXL {
  precondition(n > 0)

  if n == 1 {
    return 0
  }

  var previous: Numberick.UIntXL = 0
  var current: Numberick.UIntXL = 1

  for _ in 2 ... n {
    let next = previous + current
    previous = current
    current = next
  }

  return current
}

func numberick_inout(_ n: Int) -> Numberick.UIntXL {
  precondition(n > 0)

  if n == 1 {
    return 0
  }

  var previous: Numberick.UIntXL = 0
  var current: Numberick.UIntXL = 1

  for _ in 2 ... n {
    previous += current
    swap(&previous, &current)
  }

  return current
}

struct Result {
  let name: String
  let count: Int
  let fibDuration: ContinuousClock.Duration
  let printDuration: ContinuousClock.Duration

  fileprivate init(
    _ name: String,
    _ count: Int,
    _ fibDuration: ContinuousClock.Duration,
    _ printDuration: ContinuousClock.Duration
  ) {
    self.name = name
    self.count = count
    self.fibDuration = fibDuration
    self.printDuration = printDuration
  }
}

if CommandLine.arguments.count != 2 {
  print("[Swift] Missing 'repeat_count' argument.")
  exit(1)
}

let repeatCount = Int(CommandLine.arguments[1])!
let clock = ContinuousClock()
var results = [Result]()

// Test if correct - START
let testCount = 1000
let testExpected = "43466557686937456435688527675040625802564660517371780402481729089536555417949051890403879840079255169295922593080322634775209689623239873322471161642996440906533187938298969649928516003704476137795166849228875"
precondition(attaswift(testCount).description == testExpected, "INCORRECT: attaswift")
precondition(attaswift_inout(testCount).description == testExpected, "INCORRECT: attaswift_inout")
precondition(violet(testCount).description == testExpected, "INCORRECT: violet")
precondition(violet_inout(testCount).description == testExpected, "INCORRECT: violet_inout")
precondition(numberick(testCount).description == testExpected, "INCORRECT: numberick")
precondition(numberick_inout(testCount).description == testExpected, "INCORRECT: numberick_inout")
// Test if correct - END

for count in [10000, 30000, 100000, 300000, 1000000] {
  for _ in 0..<repeatCount {
    do {
      var result: Attaswift.BigInt = 0
      let fibDuration = clock.measure { result = attaswift(count) }
      let printDuration = clock.measure { print(result)}
      let r = Result("Attaswift", count, fibDuration, printDuration)
      results.append(r)
    }

    // do {
    //   var result: Attaswift.BigInt = 0
    //   let fibDuration = clock.measure { result = attaswift_inout(count) }
    //   let printDuration = clock.measure { print(result)}
    //   let r = Result("Attaswift_inout", count, fibDuration, printDuration)
    //   results.append(r)
    // }

    do {
      var result: Violet.BigInt = 0
      let fibDuration = clock.measure { result = violet(count) }
      let printDuration = clock.measure { print(result)}
      let r = Result("Violet", count, fibDuration, printDuration)
      results.append(r)
    }

    // do {
    //   var result: Violet.BigInt = 0
    //   let fibDuration = clock.measure { result = violet_inout(count) }
    //   let printDuration = clock.measure { print(result)}
    //   let r = Result("Violet_inout", count, fibDuration, printDuration)
    //   results.append(r)
    // }

    do {
      var result: Numberick.UIntXL = 0
      let fibDuration = clock.measure { result = numberick(count) }
      let printDuration = clock.measure { print(result)}
      let r = Result("Numberick", count, fibDuration, printDuration)
      results.append(r)
    }

    // do {
    //   var result: Numberick.UIntXL = 0
    //   let fibDuration = clock.measure { result = numberick_inout(count) }
    //   let printDuration = clock.measure { print(result)}
    //   let r = Result("Numberick_inout", count, fibDuration, printDuration)
    //   results.append(r)
    // }
  }
}

func sortFn(lhs: Result, rhs: Result) -> Bool {
  if lhs.name == rhs.name {
    return lhs.count < rhs.count
  }

  return lhs.name < rhs.name
}

func toString(_ d: ContinuousClock.Duration) -> String {
  return String(describing: d).replacing(" seconds", with: "")
}

let file = FileHandle(forUpdatingAtPath: "results.txt")!
try! file.seekToEnd()

for r in results.sorted(by: sortFn) {
  let f = toString(r.fibDuration)
  let p = toString(r.printDuration)
  let line = "\(r.name),\(r.count),\(f),\(p)\n"
  let data = Data(line.utf8)
  try! file.write(contentsOf: data)
}

try file.close()
