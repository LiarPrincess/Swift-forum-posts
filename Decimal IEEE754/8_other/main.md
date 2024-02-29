## Swift evolution

Where do we put `Decimal`?
- stdlib - this way we would have `Float/Double` and `Decimal` in the same place which makes sense given how "symmetrical" those types are - same thing different radix.

  This would also allow us to place `Decimal` in the Swift book in the [Floating-Point-Numbers](https://docs.swift.org/swift-book/documentation/the-swift-programming-language/thebasics#Floating-Point-Numbers) section. This could ease the confusion the new programmers face: how to represent money? Hmm… the Swift book mentioned:

  > Floating-point numbers are numbers with a fractional component, such as 3.14159, 0.1, and -273.15.
  >
  > (…)
  >
  > In situations where either type would be appropriate, `Double` is preferred.

  Oh! Yes! `Double` is probably the right choice!

  Anyway, if we want `Decimal` in stdlib then it has to go through Swift evolution. Not having `UInt128` could be a certain problem, because I am almost 100% sure that the `Decimal128` would need to expose some property with this type.

  We may want to add `typealias Float64 = Double`. There was a discussion about this on this forum, a few people from this thread also participated in it.

- Foundation - I don't see the reason why . As far as I know the new Foundation design does not contain it.

- Swift Numerics - I see it as more of a "staging" environment where work on with it before moving to stdlib.

- separate repo - oh-my-decimal contains a lof of the supporting infra (Python scripts, code generators, test suites etc.). I assume this would also be true for the official `Decimal` type. A separate "staging" (before stdlib) repo may be better, because you do not have to worry about the other Swift Numerics thingies.

## Transcendental functions

Oh-my-decimal does not implement any transcendentals. `Decimal.pow(exponent: Int)` may be useful, but it is not a must-have.

## Exists?

@scanon @xwu
If I were tasked with designing `FloatingPoint/BinaryFloatingPoint` protocols I would also do a rough sketch for `DecimalFloatingPoint` to decide what goes to `FloatingPoint` and what goes to `BinaryFloatingPoint/DecimalFloatingPoint`. Does such document exist at Apple? Can it be made public?

## Google summer of code

I'm not really sure if `Decimal` is the best project GSOC.

`Decimal` is all about the precision, so writing it takes more time than usual code. In practice you can't write a decimal without bugs:
-  [Hossam A. H. Fahmy tests](http://eece.cu.edu.eg/~hfahmy/arith_debug/) found bugs in (taken from their website):
   - decimal64 and decimal128 designs of SilMinds
   - FMA and Sqrt operations of decNumber developed by Dr. Mike Cowlishaw. This is the same Mike Cowlishaw who was an editor of standard 2008 and the person responsible for [speleotrove.com/decimal](https://speleotrove.com/decimal/).
   - FMA for decimal128 in the Intel library by Dr. Marius Cornea
- Intel still has errors in tests:
  - few lines with invalid result
  - few lines that work, but have incorrect format: missing expected `status`, `next` is a binary operation etc.
- even [Hossam A. H. Fahmy tests](http://eece.cu.edu.eg/~hfahmy/arith_debug/) have 1 incorrect FMA line
- oh-my-decimal - I wrote this -> it is bad

Also, `Decimal` requires an enormous amount "warm up" time before you have something to show:
- reading and understanding standard - this is non-trivial, because most programmers are not accustomed to thinking in IEEE 754 - the standard was designed to "just work" in most common cases.
- designing protocol/types - this is what this thread is all about
- getting accustomed to how decimal arithmetic works - mostly playing with Intel library, there are a few surprises
- (maybe) writing a wrapper for Intel lib - this is how oh-my-decimal started. I would highly recommend this approach, because you can just port up to the next `return` statement.

All that would probably use half of the time, and we have not even started writing the actual implementation.

But wait! We forgot about something! Tests! Oh-my-decimal has:
- [Intel tests](https://www.intel.com/content/www/us/en/developer/articles/tool/intel-decimal-floating-point-math-library.html) - Python script generates Swift unit tests.
- [Speleotrove tests](https://speleotrove.com/decimal/) - Python script generates Swift unit tests.
- [Hossam A. H. Fahmy tests](http://eece.cu.edu.eg/~hfahmy/arith_debug/)
- [oh-my-decimal-tests](https://github.com/LiarPrincess/Oh-my-decimal-tests) - tests generated using Python `decimal` module
- unit tests written by hand - they still take a few days to write

But don't despair!

…

Yet.

…

How about:
- you can't just write `Decimal` according to the standard, it has to work similar to `Swift.Double` because this is what users expect.
- writing your own `UInt128` - `DoubleWidth` from SwiftNumerics [crashes or gives incorrect results](https://github.com/apple/swift-numerics/issues/272). Oh-my-decimal also has `UInt256`, you can write `Decimal` without it but it would much more difficult. For FMA you may need `3x bitWidth` (`UInt96`, `UInt192`, `UInt384`).
- compiler bugs - compiling arrays with 1000 elements (`UInt256`) should not take 15 min and 20GB of ram. Thb. I never managed to finish this build. I decided to split those tables with Python script.

That's a sizeable number of tasks. And you are working with a person with whom you have never worked before. I also saw that some of the possible participants had no Swift experience, so that would add more time. I know that a lof of people would help the student, and the scope can be reduced to: properties, `+`, `-`, `*`, `/`, `reminderNear`, `quantization`, `compare` (definitely not FMA or binary floating point interop), but…

Having written `Decimal` and [BigInt](https://github.com/LiarPrincess/Violet) ([twice](https://github.com/LiarPrincess/Violet-BigInt-XsProMax)) I think that `BigInt` is more suitable for GSOC. It is easier and more self-contained (meaning that when you finish a certain part you know that it mostly works, while in `Decimal` it is more of a "how many bugs are there"). You could for example:
- 2 weeks - setup/design/discussions
- 4 weeks - implementation - most basic version. Just the school math, not Karatsuba etc.
- 3 weeks - writing tests + some basic performance tests
- 3 weeks - one of:
  - performance improvements to basic operations
  - implementation of 1 advanced mul/div algorithm

I think that `BigInt` is just easier to introduce to a new person, most of the time they already know what to do. Though the question would be: which one is more needed?

## @mgriebling

### Intel unit tests

I see that you use [an array of test cases](https://github.com/mgriebling/DecimalNumbers/blob/b223205904f06d0e4056a87e5c86e61a10737f5d/Tests/DecimalNumbersTests/Decimal32Tests.swift#L99) and execute them as 1 unit test.

Oh-my-decimal uses a Python script to transform Intel tests into Swift unit tests. This way you have more tooling support, and you can execute tests in parallel which makes them faster.

### Tables

> @mgriebling wrote:
>
> Intel's goal was to use copy & paste as much as possible. :wink: They also have lots of hardcoded numbers and obscure look-up tables, many of which have been replaced.

It is a truth universally acknowledged, that tables "do not scale" in generic contexts. Though I would still try to use them as much as possible.

For example in power of 10 you have (quick note: this and `DecimalDigitCount` are 2 most used tables):

```swift
// mgriebling code
// https://github.com/mgriebling/DecimalNumbers/tree/main

/// Returns ten to the `i`th power or `10^i` where `i ≥ 0`.
static func power10<T:FixedWidthInteger>(_ i:Int) -> T { _power(T(10), to:i) }

func _power<T:FixedWidthInteger>(_ num:T, to exp: Int) -> T {
  // Zero raised to anything except zero is zero (provided exponent is valid)
  guard exp >= 0 else { return T.max }
  if num == 0 { return exp == 0 ? 1 : 0 }
  var z = num
  var y : T = 1
  var n = abs(exp)
  while true {
    if !n.isMultiple(of: 2) { y *= z }
    n >>= 1
    if n == 0 { break }
    z *= z
  }
  return y
}
```

While oh-my-decimal uses tables:

```swift
extension Tables {

  /// Usage: `let pow10: UInt64 = Tables.getPowerOf10(exponent: 3)`.
  internal static func getPowerOf10<T: FixedWidthInteger>(exponent index: Int) -> T {
    assert(index >= 0, "Negative exponent in pow10?")

    if index < data128.count {
      let r = data128[index]
      assert(r <= T.max)
      return T(truncatingIfNeeded: r)
    }

    let index256 = index - data128.count
    let r = data256[index256]
    assert(r <= T.max)
    return T(truncatingIfNeeded: r)
  }
}
```

I think it boils down to performance, but I have not measured it:
- If you have a single decimal operation then manual calculation may be faster, because table lookup may miss cache. But single decimal operation will rarely be a performance problem, you clearly do not do enough calculations for this to matter.
- If you have multiple decimal operations (in a loop etc.) then tables may be faster because lookups will be fast. For example if we need to call `Tables.getPowerOf10(x)` 1000 times then manual calculation will re-calculate similar numbers over and over again, and multiplication is quite expensive operation.

Btw. I think that Intel code is generated - nobody wants to write the same thing 3 times, especially when dealing with such a precise code. They probably have 1 abstract decimal and they generate code 3 times for different formats.

### bid_factors

```swift
// mgriebling code
// https://github.com/mgriebling/DecimalNumbers/tree/main

/// Table of division factors of 2 for `n+1` when `i` = 0, and factors of 5
/// for `n+1` when `i` = 1 where 0 ≤ `n` < 1024. When both are factors,
/// return divisors of both are combined.  For example when `n` = 19, `n+1`
/// or 20 is a factor of both 2 and 5, so the return for `i=0` is 2 (not 4),
/// and `i=1` is 1.  This function reproduces the contents of the table
/// `bid_factors` in the original.
static func bid_factors(_ n:Int, _ i:Int) -> Int {
  var n = n + 1
  if i == 0 && n.isMultiple(of: 2) {
    var div2 = 1
    n /= 2
    while n.isMultiple(of: 5) { n /= 5 } // remove multiples of 5
    while n.isMultiple(of: 2) { div2 += 1; n /= 2 }
    return div2
  } else if i == 1 && n.isMultiple(of: 5) {
    var div5 = 1
    n /= 5
    while n.isMultiple(of: 2) { n >>= 1 }
    while n.isMultiple(of: 5) { div5 += 1; n /= 5 }
    return div5
  }
  return 0
}
```

I'm not sure if you have to divide by the other factor. 2 and 5 are relatively prime, so if you do factorization (Wikipedia calls it [fundamental theorem of arithmetic
](https://en.wikipedia.org/wiki/Fundamental_theorem_of_arithmetic); such a posh name) then they will be in "separate buckets". I have not tested this. Oh-my-decimal uses tables.
