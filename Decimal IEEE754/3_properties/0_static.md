## Static properties

```swift
static var nan: Self { get }
static var signalingNaN: Self { get }
static var infinity: Self { get }
static var pi: Self { get }
static var zero: Self { get }

static var leastNonzeroMagnitude: Self { get }
static var leastNormalMagnitude: Self { get }
static var greatestFiniteMagnitude: Self { get }

// Default on protocol:
static var radix: Int { 10 }
```

- `0` - which cohort/sign/exponent? In Oh-my-decimal it is `0E+0`.
- `leastNormalMagnitude` - which cohort? In Oh-my-decimal: `Decimal64.leastNormalMagnitude = 1000000000000000E-398` - all 'precision' digits filled = lowest exponent.
- `greatestFiniteMagnitude` - interestingly this one has to use `pack`. You can't just use `Self.maxDecimalDigits` and `Self.maxExponent` because `Decimal128` does not need the `11` in combination bits (though this is an implementation detail).
- `pi` should be rounded `.towardZero`.

For nerds we can have:

```swift
static var is754version1985: Bool { return false }
static var is754version2008: Bool { return true }
```

Oh-my-decimal defines this on `DecimalFloatingPoint` protocol - we know that all of our implementations share the same values. Swift should do it on each `Decimal` type separately (or just skip it). We can do this because `Decimal` is implemented in software. Idk if Swift guarantees that binary floating point operations conform to a particular version of the standard.

As for the @mgriebling implementation:

```swift
// mgriebling code
// https://github.com/mgriebling/DecimalNumbers/tree/main
public struct Decimal32 : Codable, Hashable {

  public static var greatestFiniteMagnitude: Self {
    Self(bid:ID(expBitPattern:ID.maxEncodedExponent, sigBitPattern:ID.largestNumber))
  }

  public static var leastNormalMagnitude: Self {
    Self(bid:ID(expBitPattern:ID.minEncodedExponent, sigBitPattern:ID.largestNumber))
  }

  public static var leastNonzeroMagnitude: Self {
    Self(bid: ID(expBitPattern: ID.minEncodedExponent, sigBitPattern: 1))
  }

  public static var pi: Self {
    Self(bid: ID(expBitPattern: ID.exponentBias-ID.maximumDigits+1, sigBitPattern: 3_141593))
  }
}
```

- `leastNonzeroMagnitude` is basically `1`, so you don't have to `pack`:
  - sign = 0 -> positive
  - exponent = 0 -> `0 - Self.exponentBias`
  - significand = 1

- `leastNormalMagnitude` is equal `b^Emin = 10^Emin`, try this:

  ```swift
  func test_xxx() {
    let lnm = Decimal32.leastNormalMagnitude
    let down = lnm.nextDown
    print(lnm, lnm.isNormal) // 9.999999e-95 true
    print(down, down.isNormal) // 9.999998e-95 true
  }
  ```

  We were `leastNormalMagnitude` and we went toward `0` -> the 2nd line should be `false`. You can use binary search to find the correct `leastNormalMagnitude` (it will converge quite fast) and then just encode it directly.

- `pi` - you can use this as a unit test (rounding has to be: `.towardZero`!):

  ```swift
  let string = "3.141592653589793238462643383279502884197169399375105820974944592307816406286208998628034825342117067982148086513282306647"
  let expected = T(string, rounding: .towardZero, status: &status)
  XCTAssertEqual(…)
  ```
