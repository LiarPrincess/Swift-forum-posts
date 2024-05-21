# What to use? (spoiler: GMP)

Ok, let's say that we have to choose some `BigInt` library. Which one?

First of all there is no "one `BigInt` library to rule them all". It all depends. As already said Violet has 2 versions:

- [Violet](https://github.com/LiarPrincess/Violet) - inlined `Int32` or a heap allocation.
- [Violet-BigInt-XsProMax](https://github.com/LiarPrincess/Violet-BigInt-XsProMax) - only heap.

In most of the tests "Violet-BigInt-XsProMax" [is slightly faster](https://github.com/apple/swift-numerics/pull/256#issuecomment-1416165556) because it does not have to check with which representation we are dealing with. But in [swift-numerics/pull/120](https://github.com/apple/swift-numerics/pull/120) @xwu proposed a π calculation test.

![Violet is faster in pi calculation](pi-test.png)

In this test "Violet" is much faster than "Violet-BigInt-XsProMax", getting similar results as much more optimized Python (the numbers that we are dealing with are huge, and Violet naive `div` is slow). The reason is the input distribution for multiplication. For example for `test_pi_5000` (row/column is operand length, value is operation count; full distribution for all operations is [available here](https://github.com/LiarPrincess/Swift-BigInt-performance-tests/blob/pi-input-distribution/result.md)):

|lhs/rhs|0|
|-|-|
|0|8067|
|200|6795|
|400|6470|
|600|6234|
|800|6069|
|and so on…||

The `rhs` is always a single `Word`, most probably in `Int32` range. This is exactly the case that Violet was optimized for because it does not have to allocate memory.

Bottom line is: know your number distribution.

- BigInt
  - Assumes that most of the code will use built-in Swift integer types. `BigInt` will be used, but only in places that can overflow.
  - Focuses on performance for big numbers, since small ones will be handled using Swift types.
  - Is more of a auxiliary type, than a thing on its own.
- Unlimited/general purpose integer (I made-up this name, so don't Google it):
  - Assumes that this is the only integer type available in the system.
  - Will probably optimise for small numbers (think: 0, 1, 256 etc.) rather than big ones (think: 123_123_123_123_123_123).

Fibonacci is `BigInt`, but if we were implementing a math library and wanted to give our users a nice `Int` type then "general purpose integer" could be better. Interestingly Python `int` type is unlimited - there is no `BigInt` library because the default `int` is a `BigInt`.


As far as currently available Swift libraries go:

- 🔴 [Swift numerics/biginteger](https://github.com/apple/swift-numerics/tree/biginteger) - [please don't](https://github.com/apple/swift-numerics/issues/242)

- 🟡 [Numberick](https://github.com/oscbyspro/Numberick) by @oscbyspro
  - I don't know anything about their implementation
  - they only have `BigUInt`? I wanted to run Violet tests on it and they require `BigInt`
  - for `mul` they use Karatsuba [above 20 words](https://github.com/oscbyspro/Numberick/blob/main/Sources/NBKCoreKit/Private/NBKStrictUnsignedInteger%2BMultiplication.swift#L32) - this is around the expected value (usually between 20 and 40 depending on the implementation details). Attaswift [limit is 1024](https://github.com/attaswift/BigInt/blob/master/Sources/Multiplication.swift#L84), which is uncommon.

- 🟢 Attaswift
  - Violet tests were merged, but some of them were commented
  - [#115 bitWidth is wrong for -(power-of-two)](https://github.com/attaswift/BigInt/issues/115) by @wadetregaskis is related to [those commented tests](https://github.com/attaswift/BigInt/blob/master/Tests/BigIntTests/Violet/BigIntPropertyTests.swift#L60) from Violet
  - [#99 [Violet] Node tests](https://github.com/attaswift/BigInt/pull/99) says that `xor` may sometimes be incorrect (PR contains detailed description):

    ```swift
    // Attaswift returns '0'
    self.xorTest(lhs: "-1", rhs: "18446744073709551615", expecting: "-18446744073709551616")
    ```
  - [#99 [Violet] Node tests](https://github.com/attaswift/BigInt/pull/99) says that shift right uses different rounding than `Swift` (PR contains detailed description):

    ```swift
    // Attaswift returns '60397977'.
    self.shiftRightTest(value: "-1932735284", count: 5, expecting: "-60397978")
    ```

    Attaswift is slightly inconsistent with the rest of the Swift:

    |Engine|Result|
    |-|-|
    |attaswift/BigInt|-60397977|
    |[Wolfram Alpha](https://www.wolframalpha.com/input?i=-1932735284+%3E%3E+5)|-60397977|
    |Node v17.5.0|-60397978|
    |Python 3.7.4|-60397978|
    |Swift 5.3.2|-60397978|
    |Violet|-60397978|

    (Yes, all of the results in the table are correct.)

    I think that attaswift uses sign + magnitude representation. If it was 2 complement then everything would be trivial, but it is not, so sometimes you need an adjustment: Swift uses what would be `GMP_DIV_FLOOR` mode in `GMP`. Which means that if we are negative and any of the removed bits is `1` then we have to round down.


Anyway, if my goal was to use 100% Swift then I would go with Attaswift.

That said, I don't think anyone goal is to use 100% Swift, but to use the best possible implementation. Because of that I would recommend using `GMP` wrapped in a `class`. It is easily the fastest and the most battle-tested option out there. Just check if it is supported on your platform.

If you need `BigInt`, but you do not need a full `BigInt`, then you may look at the wider fixed width integers:
- stdlib will get `Int128/UI128` soon - I tried 4 or 5 builds (as recent as from 2 weeks ago), and all of them crashed
- `DoubleWidth` solutions, for example:
  - [swift-numerics](https://github.com/apple/swift-numerics/blob/main/Sources/_TestSupport/DoubleWidth.swift) - few months ago [I opened an issue](https://github.com/apple/swift-numerics/issues/272) about crashes and incorrect results. This uncovered even more issues (see the connected PR). And their test suite is lacking. Just be careful and write tests.
  - [Numberick](https://github.com/oscbyspro/Numberick) also has one. At some point I opened an issue there, but it was solved quite quickly.
- `DoubleWidth` may be slow as soon as you reach multiplication on `UInt256`, so it may be better to just [use `4x UInt64` and schedule 16 (independent!) multiplications one after the other](https://github.com/LiarPrincess/Oh-my-decimal/blob/mr-darcy/Sources/Decimal/Generated/UInt256.swift#L404).

A quick indicator of the quality is the `div` function, if you see any `>> 1` (which indicates bit-by-bit division) then run away.

Do not go too crazy with fixed width integers, `Int128/Int256` are fine, but above that YMMW. I have a Python script that will generate `UInt128` (as `2x UInt64`) and `UInt256` (as `4x UInt64`) for me. I never had to use anything bigger.
