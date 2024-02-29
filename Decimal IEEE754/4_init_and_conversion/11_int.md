## Int -> Decimal

```swift
// Default rounding: toNearestOrEven
init<Source: BinaryInteger>(_ value: Source, rounding: DecimalFloatingPointRoundingRule, status: inout DecimalStatus)
init<Source: BinaryInteger>(_ value: Source, rounding: DecimalFloatingPointRoundingRule)
init<Source: BinaryInteger>(_ value: Source, status: inout DecimalStatus)
init<Source: BinaryInteger>(_ value: Source)

// If you have 'DecimalStatus' then default implementation on the protocol.
// Otherwise a protocol requirement.
init?<Source: BinaryInteger>(exactly source: Source) {
  // This method raises:
  // - isInexact -> fail
  // - isOverflowInexact -> fail
  // - isUnderflowInexact -> fail
  // 'rounding' should not matter because any rounding means 'inexact'.
  var status = DecimalStatus()
  let rounding = DecimalFloatingPointRoundingRule.towardZero
  self = Self(source, rounding: rounding, status: &status)

  if status.isInexact {
    return nil
  }

  // Any unexpected flags?
  status.clear(.isOverflowInexact | .isUnderflowInexact)
  assert(status.isEmpty)
}

// Default implementation on protocol with 'toNearestOrEven' rounding.
init(_ value: Int) { … }
init(integerLiteral value: Int) { … }
```

If you have `DecimalStatus` then you don't need the `exactly` conversion (`init?<Source: BinaryInteger>(exactly:)`), because user could just check the `isInexact`. Oh-my-decimal has it to be more like `Double`.

If you do NOT have `DecimalStatus` then you need the `exactly` conversion - that's the whole point of it -> plumbing for the missing flags.

## Decimal -> Int

```swift
// Example for 'Decimal32'.
extension FixedWidthInteger {

  // Default rounding: towardZero
  init(_ source: Decimal32, rounding: DecimalFloatingPointRoundingRule)
  init(_ source: Decimal32)

  init?(exactly source: Decimal32)
}
```

We can't forget about this operation! It is not defined on decimal, but on `Int`.

Remarks:
- you may want to attach those methods to some other `Int` protocol. Oh-my-decimal used `FixedWidthInteger`, to block any `BigInt` implementations (they are not supported!).
- you may also want to use generic `init<T: DecimalFloatingPoint>(_:rounding:)`. Oh-my-decimal has overloads for every decimal type because the actual method is implemented on `internal protocol DecimalMixin`, so we either have to force-cast to `DecimalMixin`, or to make `DecimalMixin` public.

Interestingly this is the weirdest place to implement if you support `DecimalStatus` (flags). You can't use `DecimalStatus`, because you need to replicate the `Double` behavior. For example: converting `NaN` or `infinity` should crash. In the `DecimalStatus` implementation you would probably just raise `InvalidOperation` flag, but this not what Swift users are used to! They expect crash!

No `DecimalStatus` also mean that you have to implement the `init?(exactly:)` method to compensate for the missing `isInexact` flag.
