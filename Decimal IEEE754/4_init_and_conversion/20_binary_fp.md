## Float -> Decimal

Example for `Float`:

```swift
// Default rounding: toNearestOrEven
init(_ value: Float, rounding: DecimalFloatingPointRoundingRule, status: inout DecimalStatus)
init(_ value: Float, rounding: DecimalFloatingPointRoundingRule)
init(_ value: Float, status: inout DecimalStatus)
init(_ value: Float)

init?(exactly value: Float, status: inout DecimalStatus)
init?(exactly value: Float)
```

Normally `exactly` does not have a `status` argument, but Intel has a special `isBinaryFloatingPointSubnormal` flag.

Oh-my-decimal copied this code (and tables) from Intel. There are some minor changes, but they do not matter…

Side-note: binary floating point interop is not required by `FloatingPoint` protocol, but we need it to fulfill the standard. That said, those conversions (both directions) should NEVER be used. `Decimal` should expose all of the needed methods, without the whole `Decimal` -> `Double` -> `pow` (or other method) -> `Decimal` dance.

WARNING: the whole binary floating point interop is heavily based on tables. Huge tables. We have to split them into a multiple smaller ones. Otherwise the compilation would take at least 15min and 20GB of ram. 'At least' because I never managed to compile it. Tbh. you can quite reliably break Swift compiler with tables with ~1000 elements, especially if they contain things like `UInt256`.

## Decimal -> Float

Example for `Decimal32` -> `Float`:

```swift
extension Float {
  // Default rounding: toNearestOrEven
  init(_ source: Decimal32, rounding: DecimalFloatingPointRoundingRule, status: inout DecimalStatus)
  init(_ source: Decimal32, rounding: DecimalFloatingPointRoundingRule)
  init(_ source: Decimal32, status: inout DecimalStatus)
  init(_ source: Decimal32)

  init?(exactly source: Decimal32)
}
```

Again, copy-paste from Intel.

Swift probably wants to re-design this.
