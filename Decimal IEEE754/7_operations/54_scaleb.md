## LogB, ScaleB

```swift
associatedtype Exponent: SignedInteger & FixedWidthInteger

// In Swift this is a property, buy it can signal InvalidOperation on NaN/inf/0,
// so we also need flags.
func exponent(status: inout DecimalStatus) -> Exponent
var exponent: Exponent

var significand: Self { get }

// Default rounding: toNearestOrEven
init(
  sign: FloatingPointSign,
  exponent: Exponent,
  significand: Self,
  rounding: DecimalFloatingPointRoundingRule,
  status: inout DecimalStatus
)
init(
  sign: FloatingPointSign,
  exponent: Exponent,
  significand: Self,
  rounding: DecimalFloatingPointRoundingRule
)
init(
  sign: FloatingPointSign,
  exponent: Exponent,
  significand: Self,
  status: inout DecimalStatus
)
init(
  sign: FloatingPointSign,
  exponent: Exponent,
  significand: Self
)
```

Exponent:
- remove `FixedWidthInteger` from `associatedtype Exponent`?
- `integer format` from the standard - you can choose either `integer` or `floating-point`
- `NaN` -> `Int.max + InvalidOperation`
- `infinity` -> `Int.max + InvalidOperation`
- `0` -> `Int.min + InvalidOperation`
- finite non `0` - make it so that the `self.significand` is always `[0, 10)`

Significand:
- `qNaN` -> positive `qNaN` with payload preserved
- `sNaN` -> positive `sNaN` with payload preserved
- `infinity` -> positive `infinity`
- `-0E123` -> `+0E123` - positive with the same exponent
- finite values (including `0`) are always `[0, 10)`. Always positive - `Decimal` is implemented in software, so we can do this.

ScaleB:
- we need `rounding`
- if `significand` is `sNaN` then return `sNaN` without raising any flags. This is different than standard (`qNaN + InvalidOperation`)
- if `NaN` payload is non-canonical -> preserve it.
- if `significand` is `infinity` then use `sign` and ignore `exponent`
- finite non canonical `significand` is treated as `0` with proper sign and exponent
- adding exponents may overflow:
  - `0` (including non canonical!) -> camp to `min/max` exponent
  - finite non 0
    - 'positive' overflow -> round to `infinity/greatestFiniteMagnitude + OverflowInexact`
    - 'negative' overflow -> round to `zero/leastNonzeroMagnitude + UnderflowInexact`
- this operation can also be used to multiply by power of 10. This is quite useful, but not a lot of people know about this.

`ScaleB` axiom from `FloatingPoint` protocol:

```swift
// 'significand' property is always positive, so this works:
let d1 = -Decimal64.nan
print(Decimal64(sign: d1.sign, exponent: 0, significand: d1.significand)) // -nan 🟢
let d2 = -Double.nan
print(Double(sign: d2.sign, exponent: 0, significand: d2.significand)) // nan 🔴

// But we break '0' - it has invalid exponent
let d = Decimal128(sign: .minus, exponent: 123, significand: .zero)
print(d.significand) // 0E+123
print(d.exponent) // -9223372036854775808
print(Decimal128(
  sign: d.sign,
  exponent: d.exponent,
  significand: d.significand
)) // -0E-6176 <-- different exponent
```

If read closely the documentation for [FloatingPoint.init(sign:exponent:significand:)](https://developer.apple.com/documentation/swift/floatingpoint/init(sign:exponent:significand:)):

> For any floating-point value x of type F, the result of the following is equal to x, with the distinction that the result is canonicalized if x is in a noncanonical encoding:

So it only requires us to be equal, it does not require the same exponent. This could also be solved with `significand=0E0, exponent=current exponent`, but this goes against the standard:
> 5.3.3 logBFormat operations
>
> When logBFormat is an integer format, then logB(NaN), logB(∞), and logB(0) return language-defined values outside the range ±2 × (emax + p − 1) and signal the invalid operation exception.

Btw. I really don't like how `scaleB` documentation is written in Swift - the fragment that I quoted above. It says "any floating-point" which also includes NaN, then it says "is equal to x", NaNs are never equal.

@mgriebling:

```swift
// mgriebling code
// https://github.com/mgriebling/DecimalNumbers/tree/main
extension Decimal32 : FloatingPoint {
  public init(sign: Sign, exponent: Int, significand: Self) {
    self.bid = ID(sign: sign, expBitPattern: exponent+ID.exponentBias,
                    sigBitPattern: significand.bid.unpack().sigBits)
  }
}

struct IntDecimal32 : IntDecimal {
  init(sign:Sign = .plus, expBitPattern:Int=0, sigBitPattern:RawBitPattern) {
    self.sign = sign
    self.set(exponent: expBitPattern, sigBitPattern: sigBitPattern)
  }
}
```

I think you are supposed to add the exponent from `significand` and the `exponent` argument.

Anyway, `exponent` is an argument provided by the user, so any addition can overflow. For example I can call your method like this: `Decimal32(sign: .plus, exponent: Int.max, significand: …)`.

In Swift overflow traps.

In C (which is what Intel uses, and you may be more familiar with) it… is an interview question. C++17 – ISO/IEC 14882:2017, because I'm too lazy to check which version Intel uses:
- unsigned:
  > 6.9.1 Fundamental types [basic.fundamental]
  >
  > 4. Unsigned integers shall obey the laws of arithmetic modulo 2 n where n is the number of bits in the value representation of that particular size of integer.

  Further clarified in footnote 49:

  > 49) This implies that unsigned arithmetic does not overﬂow because a result that cannot be represented by the result unsigned integer type is reduced modulo the number that is one greater than the largest value that can be represented by the resulting unsigned integer type.

- signed (literal quote):
  > Good luck!
