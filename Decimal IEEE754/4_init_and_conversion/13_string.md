## String -> Decimal

```swift
// Default rounding: .toNearestOrEven
init?<S: StringProtocol>(_ description: S, rounding: DecimalFloatingPointRoundingRule, status: inout DecimalStatus)
init?<S: StringProtocol>(_ description: S, rounding: DecimalFloatingPointRoundingRule)
init?<S: StringProtocol>(_ description: S, status: inout DecimalStatus)
init?<S: StringProtocol>(_ description: S)

// If you have 'DecimalStatus' then default implementation on the protocol.
// Otherwise a protocol requirement.
init?<S: StringProtocol>(exactly description: S)

// === Examples ===

// Can't parse -> 'nil'.
print(Decimal32("Ala ma kota")) // nil

// NaN
// - payload is canonical -> ok
print(Decimal32("nan(999999)")) // Optional(nan(0xf423f))
print(Decimal32("nan(0xf423f)")) // Optional(nan(0xf423f))
// - payload is not canonical, but fits within mask -> accept non-canonical
//   Printing non-canonical treats payload as 0.
print(Decimal32("nan(1048574)")) // Optional(nan)
print(Decimal32("nan(0xffffe)")) // Optional(nan)
// - payload does not fit within mask -> non-canonical with all bits 1
//   Printing non-canonical treats payload as 0.
print(Decimal32("nan(1234654899198265168468168498)")) // Optional(nan)
print(Decimal32("nan(0x1234654899198265168468168498)")) // Optional(nan)

// Finite
// - inexact - Decimal32 can store only 7 most-significand digits.
//             Use 'rounding' argument to decide what to do.
var status = DecimalStatus()
let d = Decimal32("12345678", rounding: .up, status: &status)
print(d, status) // Optional(1234568E+1), isInexact
status.clearAll()
// - exponent overflow
let d = Decimal32("1234567E9999999999", rounding: .up, status: &status)
print(d, status) // Optional(inf), isInexact
status.clearAll()
```

There are tons of other edge cases when parsing. I wrote fairly exhausting unit tests for this, so you can check them out.

Oh-my-decimal does not support `formatOf-convertFromHexCharacter(hexCharacterSequence)` (section `5.4.3 Conversion operations for binary formats` from the standard).

Side-note: `String` parsing is not required by `FloatingPoint` protocol, but we need it to fulfill the standard. It is a generally useful method, so I assume that we want it.

@mgriebling:

```swift
// In their implementation initializer is non-optional, and parsing failure
// returns NaN. This is more standard-like approach. More idiomatic Swift
// would return 'nil'.
print(Decimal32("NaNaNa Batman!")) // NaN
print(Decimal32("12345678xxx"))    // NaN

// Result: Inf
// Swift.Double would return 'nil'.
print(Decimal32("infxxxxx"))
```

I'm not sure how I feel about `(x << 1) + (x << 3)`. Intel uses it (a lot), but Oh-my-decimal just does `x * 10`. Compiler should be smart enough to make things fast. Shifting will not check for overflow, so be careful (or use `x.multipliedReportingOverflow(by: 10)`).

## Decimal -> String

```swift
var description: String { get }

// === Examples ===
print(+Decimal64(nan: 0x123, signaling: false)) // nan(0x123)
print(-Decimal64(nan: 0x123, signaling: false)) // -nan(0x123)
print(+Decimal64(nan: 0x123, signaling: true)) // snan(0x123)
print(-Decimal64(nan: 0x123, signaling: true)) // -snan(0x123)

print(+Decimal64.infinity) // inf
print(-Decimal64.infinity) // -inf

print(Decimal64.zero) // 0E+0
print(Decimal64.greatestFiniteMagnitude) // 9999999999999999E+369

print(Decimal64("123")!) // 123E+0
print(Decimal64("-123")!) // -123E+0
print(Decimal64("123E2")!) // 123E+2
print(Decimal64("12300E0")!) // 12300E+0
```

Oh-my-decimal returns unambiguous value in the following format: `[-][significand]E[signed exponent]`. Note that no within-cohort modification happens (`123E+2 == 12300E+0` but they are printed differently) and the exponent is always present even if it is `0`.

Swift probably also wants `NumberFormatter`.
