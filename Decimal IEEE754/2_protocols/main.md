## FloatingPoint

You can, but you do not get a lot from it.

We all know what the final `Decimal` type in Swift will conform to `FloatingPoint`, so the discussion here is a little bit pointless, but:

There are not a lot of functions that could work on `Decimal/BinaryFloatingPoint` (or `Int` if we talk about `AdditiveArithmetic/Numeric`) and be correct on all of them. Writing code that works on just `Decimal` is difficult, and as soon as you introduce multiplication (for example `price * quantity`) you almost always want to specialize to `Decimal`. `Decimals` have their own homogenous arithmetic, so you tend to use it exclusively instead of being generic.

In fact, in 99.9% of the cases you use only 1 `Decimal` type (most probably `Decimal128`), and specialize everything to it. You don't even use `DecimalFloatingPoint`, this protocol is more of a "decimal semantic" marker and a place where we declare common implementation (overloads with default `rounding` etc.). In binary floating point different types have different uses and tradeoffs: storage, speed, are we on CPU or GPU? For decimal you use 1 type for everything and never change it.

Not conforming to `FloatingPoint` would also allow you to support `DecimalStatus`.

As far as I know [Foundation.Decimal](https://developer.apple.com/documentation/foundation/decimal) does not conform to `FloatingPoint`. I'm not sure how many people complained about this fact.

I am not saying that the `Decimal` should not conform to `FloatingPoint` protocol. It can, but it is not nearly that useful.

## AdditiveArithmetic, Numeric

Same story as `FloatingPoint`: you can, but you do not get a lot from it. You can be generic over `DecimalFloatingPoint`. But being generic over `AdditiveArithmetic` while using `Decimal` is a little bit weird.

## ExpressibleByFloatLiteral

Swift converts to `Float80/Double` and then converts to a number.
This conversion may not be exact, so it is basically a random number generator.

If this gets fixed then: yes.

I see people proposing a new `protocol` for this, but can't we just use `ExpressibleByFloatLiteral`? We would need to add a new type to `associatedtype FloatLiteralType: _ExpressibleByBuiltinFloatLiteral`. This should be purely additive, because `Float/Double/Float80` would use `Float/Double/Float80` (same as currently - no changes).

The design of the new `_ExpressibleByBuiltinFloatLiteral` type is out of scope here, but you need to support compiler errors for `isInexact` and hex character sequences for (quote from standard):

> 5.4.3 Conversion operations for binary formats<br/>
> Implementations shall provide the following formatOf conversion operations to and from all supported binary floating-point formats; these operations never propagate non-canonical floating-point results.<br/>
> ― `formatOf-convertFromHexCharacter(hexCharacterSequence)`<br/>
> See 5.12 for details.<br/>
> ― `hexCharacterSequence convertToHexCharacter(source, conversionSpecification)`<br/>
> See 5.12 for details. The conversionSpecification specifies the precision and formatting of the hexCharacterSequence result.

Or maybe that's not possible. I have not looked at this. Anyway, as long as the future `ExpressibleByFloatLiteral` can express `Decimal` then this discussion is completely orthogonal to the issue raised in this thread.

## ExpressibleByIntegerLiteral

Oh-my-decimal has it.

Required by `Numeric` protocol, and as we know `FloatingPoint` requires `Numeric`.

## Codable

Yes!

But how? We need to preserve sign/exponent/significant/cohort/payload/signaling bit etc. What do we do with non-canonical values?

Oh-my-decimal uses binary encoding (`BID`). We need to remember that receiver may not support parsing `UInt128` - most of the languages stop at `UInt64`, the worst case would be if they tried to parse it as `Double` (ekhm… JavaScript). If we store each value as `String` then it should not be a problem -> they will fix it in post-processing. Why `BID` not `DPD`? It was easier for me.

| Decimal      | Encoded positive | Encoded negative |
|--------------|--------------|--------------|
| nan(0x123)   | "2080375075" | "4227858723" |
| snan(0x123)  | "2113929507" | "4261413155" |
| inf          | "2013265920" | "4160749568" |
| 0E-101       | "0"          | "2147483648" |
| 0E+0         | "847249408"  | "2994733056" |
| 0E+90        | "1602224128" | "3749707776" |
| 1E-101       | "1"          | "2147483649" |
| 1000000E-101 | "1000000"    | "2148483648" |
| 9999999E+90  | "2012780159" | "4160263807" |

We could also use unambiguous `String` representation (described below in "Decimal -> String" section), but:
- not canonical values will be encoded as `0` - this matches the "shall not propagate non-canonical results" from the standard.
- parsing `Decimal` is slower than `Int` - but probably fast enough that we can get away with it.
- different systems have different NaN payload encodings - not sure how much we care about them.

```swift
print(+Decimal64(nan: 0x123, signaling: false)) // nan(0x123)
print(-Decimal64(nan: 0x123, signaling: true)) // -snan(0x123)

print(+Decimal64.infinity) // inf

print(Decimal64.zero) // 0E+0
print(Decimal64.greatestFiniteMagnitude) // 9999999999999999E+369

print(Decimal64("123")!) // 123E+0
print(Decimal64("-123")!) // -123E+0
print(Decimal64("123E2")!) // 123E+2
print(Decimal64("12300E0")!) // 12300E+0, same value as above, different cohort
```

I'm not sure what is the correct answer for Swift. `String` representation is not a bad choice, even with all of its drawbacks.

@mgriebling I think you are missing `Codable`.

## Sendable

Yes!

Fortunately this is not a problem, as long as `UInt128` is also `Sendable`.

Note that using `Decimals` in `Tasks/threads` becomes more difficult if we store our `rounding` as a `static` property.

Though I would take `static` property over not having access to `rounding` at all - there is a quite popular `Money` type on github that has hard-coded `nearestEven`. THIS IS NOT LEGAL FOR EURO AND PLN (PLN = currency in Poland, obviously rounding mode is not connected to currency). I will not link to this repository.

Oh-my-decimal takes `rounding` as a method argument. This way we can just throw as many cores as we have at the problem. [Hossam A. H. Fahmy test suite](http://eece.cu.edu.eg/~hfahmy/arith_debug/) and [oh-my-decimal-tests](https://github.com/LiarPrincess/Oh-my-decimal-tests) already take 10 min, and I don't even want to know how long they would take in serial execution.

You could also introduce `context` which stores the rounding method. Then every operation is done by context. `Python` [allows you to do this](https://docs.python.org/3/library/decimal.html#context-objects). This is how [oh-my-decimal-tests](https://github.com/LiarPrincess/Oh-my-decimal-tests) are written:

```Python
result = ctx_python.quantize(d, precision)
```

Another way is to store the `rounding` in thread local storage, but I would not recommend this. It makes for an awful programmer/user experience, and it breaks spectacularly with green threads.

I would say that having `rounding` as an argument is the safest choice. But this is how oh-my-decimal works, so I am biased. Official Swift `Decimal` may have some different needs. Or maybe we do not need `rounding` at all? Just `quantize(to:rounding:status:)` and `round(_:status:)`, and that's it. I have seen such implementations.

@mgriebling I think you are missing `Sendable`.

## Strideable

Oh-my-decimal does not conform to this protocol.
What is the distance between `greatestFiniteMagnitude` and `leastNormalMagnitude`? You can make it work, but I'm not sure if there is a clear use-case for this. I can't think of any.

`Double` [has this](https://github.com/apple/swift/blob/main/stdlib/public/core/FloatingPointTypes.swift.gyb#L1271), so we will probably also need it.

## Random

Kind of weird for floating point. Apart from a few specific input ranges it would not do what user wants:
- simple random between 0 and 10 would be skewed towards smaller numbers because more of them are representable - tons of possible negative exponents.
- if we generated truly random (infinitely precise) value and rounded then bigger numbers would be more common - they have bigger ulp.

Oh-my-decimal does not have it.

`Double` does, and so should future `Decimal` type.
