## Decimal -> Decimal

Example for `Decimal64`:

```swift
// Default rounding: toNearestOrEven

// Converting from smaller to bigger format is always exact:
// - Decimal32 -> Decimal64
// - Decimal32 -> Decimal128
// - Decimal64 -> Decimal128
init(_ value: Decimal32)

// Converting from bigger to smaller format may be inexact:
// - Decimal64 -> Decimal32
// - Decimal128 -> Decimal32
// - Decimal128 -> Decimal64
init(_ value: Decimal128, rounding: DecimalFloatingPointRoundingRule, status: inout DecimalStatus)
init(_ value: Decimal128, rounding: DecimalFloatingPointRoundingRule)
init(_ value: Decimal128, status: inout DecimalStatus)
init(_ value: Decimal128)

init?(exactly value: Decimal128)
```

Method signatures depend on the type -> we can't have them on the `DecimalFloatingPoint` protocol.

Small -> big:
- sNaN -> sNaN, no flags raised. This is a departure from: `Double(Float.signalingNaN)` which returns `qNaN`.
- NaN payload is moved left - multiplied by a power of 10 - this is what Intel does
- finite non-canonical in smaller format will be `0` in bigger format even if the bigger significand could potentially fit the value

Big -> small:
- sNaN -> sNaN, no flags raised
- NaN payload will be moved right - divided by a power of 10 - this is what Intel does
- possible inexact, or even underflow/overflow
- `Decimal128` -> `Decimal32` is surprisingly easy to write

We will also need an interop with `Decimal` from the old `Foundation`.
