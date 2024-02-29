## Quantum

```swift
var quantum: Self { get }

// Default rounding: .toNearestOrEven
func quantized(to other: Self, rounding: DecimalFloatingPointRoundingRule, status: inout DecimalStatus) -> Self
func quantized(to other: Self, rounding: DecimalFloatingPointRoundingRule) -> Self
func quantized(to other: Self, status: inout DecimalStatus) -> Self
func quantized(to other: Self) -> Self

mutating func quantize(to other: Self, rounding: DecimalFloatingPointRoundingRule, status: inout DecimalStatus)
mutating func quantize(to other: Self, rounding: DecimalFloatingPointRoundingRule)
mutating func quantize(to other: Self, status: inout DecimalStatus)
mutating func quantize(to other: Self)

func sameQuantum(as other: Self) -> Bool

// === Examples ===

print(Decimal64.signalingNaN.quantum) // nan

let d = Decimal128("123.456789")!
let precision = Decimal128("0.01")!
var status = DecimalStatus()
let result = d.quantized(to: precision, rounding: .towardZero, status: &status)
print(result, status) // 12345E-2, isInexact
status.clearAll()

// Inexact flag will not be raised if the result is… well… exact.
let d2 = Decimal128("123.450000")!
let result2 = d2.quantized(to: precision, rounding: .towardZero, status: &status)
print(result2, status) // 12345E-2, empty

// You can't store more digits than supported by a given format.
// Doing so will result in 'nan' with 'InvalidOperation' raised.
// For example 'Decimal32' can store only 7 significand digits:
let d32 = Decimal32("1234567")!
let precision32 = Decimal32("0.1")!
let result32 = d32.quantized(to: precision32, rounding: .towardZero, status: &status)
print(result32, status) // nan, isInvalidOperation
status.clearAll()

// 'quantized' should handle 'sNaN' just like any other binary operation.
let result3 = Decimal128.signalingNaN.quantized(to: precision, status: &status)
print(result3, status) // nan, isInvalidOperation
```

Obviously you only need `quantized(to:rounding:status:) -> Self`, every other `quantize` function can be in the protocol extension.

I like the IEEE naming. `Quantum` may sound scarry, but you can get used to it

Swift already has `Double.binade`, if we went with `decade` we would have:
- `var quantum` -> `var decade` 🟢
- `func quantized(to:)` -> ? 🔴
- `func sameQuantum(as:)` -> `func sameDecade(as:)` 🟢

Python also uses [quantum](https://docs.python.org/3/library/decimal.html#decimal.Decimal.quantize), so the name is already familiar to some of the users. The "rounding" thingy (which is basically the main use for `quantize`) is mentioned in [their FAQ](https://docs.python.org/3/library/decimal.html#decimal-faq).

Btw. `quantum` property is from the standard 2019 not 2008, while `quantize` and `sameQuantum` are in both. Though the operation is quite useful (mostly when explaining how `quantized` works), so I see no harm in implementing it.

Non-IEEE option would be (I expect some name bike-shedding):

```swift
// Default rounding: .toNearestOrEven
//
// Round to 10^digitCount:
// - digitCount is positive -> 10, 100 etc.
// - digitCount = 0 -> 1 -> round to integer
// - digitCount is negative -> 0.1, 0.01 -> number of digits after the point
func rounded(digitCount: Int, direction: DecimalFloatingPointRoundingRule, status: inout DecimalStatus) -> Self
func rounded(digitCount: Int, direction: DecimalFloatingPointRoundingRule) -> Self
func rounded(digitCount: Int, status: inout DecimalStatus) -> Self
func rounded(digitCount: Int) -> Self

mutating func round(digitCount: Int, direction: DecimalFloatingPointRoundingRule, status: inout DecimalStatus)
mutating func round(digitCount: Int, direction: DecimalFloatingPointRoundingRule)
mutating func round(digitCount: Int, status: inout DecimalStatus)
mutating func round(digitCount: Int)
```
