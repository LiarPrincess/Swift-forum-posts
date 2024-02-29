## Ulp

```swift
var ulp: Self { get }
static var ulpOfOne: Self { get }
```

Intel does not have this, so as far as the implementation goes:

```swift
// mgriebling code
// https://github.com/mgriebling/DecimalNumbers/tree/main
public struct Decimal32 : Codable, Hashable {
  public var ulp: Self            { nextUp - self }
}
```

Not exactly:
- you want to use `next` away from `0` - in practice it only matters for negative powers of radix.
- `greatestFiniteMagnitude.ulp` is actually defined, but you have to go toward `0`

If you want to define `ulp` by `next + subtaraction` then:

```swift
func getUlpBySubtraction<T: DecimalFloatingPoint & DecimalMixin>(_ d: T) -> T {
  // Handle Infinity and NaN…
  assert(d.isFinite)

  let lhs: T
  let rhs: T
  let magnitude = d.magnitude
  var status = DecimalStatus()

  if magnitude.bid == T.greatestFiniteMagnitude.bid {
    lhs = magnitude
    rhs = magnitude._nextDown(status: &status)
  } else {
    lhs = magnitude._nextUp(status: &status)
    rhs = magnitude
  }

  // Next can only signal on signaling NaN, and we have already handled it.
  assert(status.isEmpty, "\(d).ulp: next signalled an exception.")

  // Rounding does not matter, because it should never round.
  // Any other status should also not happen.
  let rounding = DecimalFloatingPointRoundingRule.toNearestOrEven
  let result = lhs._subtracting(other: rhs, rounding: rounding, status: &status)
  XCTAssert(status.isEmpty, "\(d).ulp: subtraction signalled an exception.")

  return result
}
```

Alternative:

```swift
internal var _ulp: Self {
  if !self._isFinite {
    return Self(canonical: Self.nanQuietMask)
  }

  let unpack = self._unpackFiniteOrZero()

  // 0 or non-canonical?
  if unpack.significand.isZero {
    return Self._leastNonzeroMagnitude
  }

  let digitCount = Self._getDecimalDigitCount(unpack.significand)
  let exponentDecrease = Swift.min(
    BID(Self.precisionInDigits - digitCount), // fill all significand digits
    unpack.exponent.biased // biased exponent can't go below 0
  )

  let significand: BID = 1
  let exponent = unpack.exponent.biased - exponentDecrease
  return Self(canonical: exponent << Self.exponentShift_00_01_10 | significand)
}
```
