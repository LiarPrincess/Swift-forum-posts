[github.com/LiarPrincess/Oh-my-decimal](https://github.com/LiarPrincess/Oh-my-decimal) is about 95% of what you need. Almost any design of `DecimalFloatingPoint` should be a subset of what is implemented in this repository. Not tested on Apple silicon.

Vocabulary (`oh-my-decimal` uses the same names in code):

- standard - IEEE 754 2008
- standard 2019 - IEEE 754 2019
- signed exponent - human readable exponent, for example in `1E+3 = 1000` the exponent is `+3`. In `oh-my-decimal` it is represented as `Int` type.
- biased exponent - encoded exponent stored in decimal. In `oh-my-decimal` it is represented as `BID` type.
- `DecimalFloatingPointRoundingRule` - similar to `FloatingPointRoundingRule`, but without `awayFromZero` - not required by IEEE 754, not enough test cases to guarantee correctness.
- `DecimalStatus` - IEEE 754 flags: `isInvalidOperation`, `isDivisionByZero`, `isOverflow`, `isUnderflow`, and (most importantly) `isInexact`. Most of the methods have it as a last argument: `status: inout DecimalStatus`.

How this post works:

- each section starts with `oh-my-decimal` code followed by discussion. All of the examples can be run using `oh-my-decimal`.
- I will mix discussion about the protocol with my remarks to @mgriebling code from [github.com/mgriebling/DecimalNumbers](https://github.com/mgriebling/DecimalNumbers/tree/main). It may get a little messy, but is it still a discussion about the implementation, so it is not off-topic. Note that their repository does not have a LICENSE file, so if they complain I will have to remove those parts.
- I am used to [C# System.Decimal](https://learn.microsoft.com/en-us/dotnet/api/system.decimal?view=net-7.0), so you may see some influences.
- oh-my-decimal contains `DecimalStatus` (container for IEEE flags). Judging by the design of the `FloatingPoint` protocol Swift will not need this. This changes A LOT.


# Protocols

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


# Properties

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

## Properties

```swift
var isZero: Bool { get }
var isFinite: Bool { get }
var isInfinite: Bool { get }
var isCanonical: Bool { get }
var isNormal: Bool { get }
var isSubnormal: Bool { get }
var isNaN: Bool { get }
var isSignalingNaN: Bool { get }

var sign: FloatingPointSign { get }
var magnitude: Self { get }

// Default on protocol:
var floatingPointClass: FloatingPointClassification
```

- `magnitude` - if the input is non-canonical then the result should be canonical or not? Oh-my-decimal returns non-canonical (it just clears the bit).

## Binary/decimal significand encoding

```swift
associatedtype BitPattern: UnsignedInteger & FixedWidthInteger

/// IEEE-754: 5.5.2 Decimal re-encoding operations.
/// Binary integer decimal.
var binaryEncoding: BitPattern { get }
/// IEEE-754: 5.5.2 Decimal re-encoding operations.
/// Densely packed decimal.
var decimalEncoding: BitPattern { get }

init(binaryEncoding: BitPattern)
init(decimalEncoding: BitPattern)
```

On `Double` we have:

```swift
let d = Double(bitPattern: UInt64)
let bitPattern: UInt64 = d.bitPattern
```

Oh-my-decimal uses the names defined by the standard. Though those names are only for the significand part, not the whole decimal bit pattern (emphasis mine):

> 3.5 Decimal interchange format encodings
>
> c) For finite numbers, r is…
>   1) If the implementation uses the **decimal encoding** for the significand…
>   2) Alternatively, if the implementation uses the **binary encoding** for the significand, then…
>
> (And also later in '5.5.2 Decimal re-encoding operations'.)

In Swift convention it would be more like: `binaryEncodedBitPattern` with the documentation pointing that the `binary` part is only for the `significand`.

In `init` oh-my-decimal will accept non-canonical values. They will be "corrected" on read, for example `add` function will read non-canonical as `0`.

The use-cases for oh-my-decimal are:
- database does not support the given decimal format -> `binaryEncoding` -> `binary(16)`
- function is not available on oh-my-decimal -> `binaryEncoding` -> Intel lib -> `init(binaryEncoding:)`

If we want to mirror `BinaryFloatingPoint` protocol:

```swift
protocol BinaryFloatingPoint {
  associatedtype RawSignificand: UnsignedInteger
  associatedtype RawExponent: UnsignedInteger

  var exponentBitPattern: RawExponent { get }
  var significandBitPattern: RawSignificand { get }

  init(sign: FloatingPointSign,
       exponentBitPattern: RawExponent,
       significandBitPattern: RawSignificand)
}
```

- `exponentBitPattern` is always the same.
- `significandBitPattern` depends on binary/decimal encoding.

I will let the others do the name bike-shedding (maybe `binaryEncodedSignificandBitPattern` would be better, but it is worse for code completion):

```swift
associatedtype RawSignificand: UnsignedInteger
associatedtype RawExponent: UnsignedInteger

var exponentBitPattern: RawExponent { get }
/// IEEE-754: 5.5.2 Decimal re-encoding operations.
/// Binary integer decimal.
var significandBinaryEncodedBitPattern: RawSignificand { get }
/// IEEE-754: 5.5.2 Decimal re-encoding operations.
/// Densely packed decimal.
var significandDecimalEncodedBitPattern: RawSignificand { get }

init(sign: FloatingPointSign,
     exponentBitPattern: RawExponent,
     significandBinaryBitPattern: RawSignificand)

init(sign: FloatingPointSign,
     exponentBitPattern: RawExponent,
     significandDecimalBitPattern: RawSignificand)
```

---

Oh-my-decimal is on the @taylorswift side of the whole `binaryEncoding` debate. Though I was thinking about SQL (because that is what I'm used to when dealing with decimals), not databases with BSON backed.

From my experience 95+% of business operations contain either database read or write:

- if your database supports IEEE 754 (@taylorswift asked about BSON which [supports Decimal128 using BID](https://en.wikipedia.org/wiki/BSON#Data_types_and_syntax)):

     ```swift
     // Read
     // oh-my-decimal naming
     let raw: UInt128 = row.column[2]
     let decimal = Decimal128(binaryEncoding: raw)

     // Write
     var row: DatabaseRow = …
     row.column[2] = decimal.binaryEncoding
     ```

     You don't have to do anything! The decimal package already supports the conversion in both directions. You can't beat 0 lines of code, and we know that more lines of code = more bugs.

- if you database does not support IEEE 754:
  - use the decimal type supported by your database. For example [MSSQL + C# = System.Decimal](https://learn.microsoft.com/en-us/sql/relational-databases/clr-integration-database-objects-types-net-framework/mapping-clr-parameter-data?view=sql-server-ver16&viewFallbackFrom=sql-server-2014&redirectedfrom=MSDN). This has nothing to do with the `Decimal` type that we are discussing, because here you are forced to use the decimal type defined by your database driver.
  - store `Decimal` using `binary` column type -> goes back to the "your database supports IEEE 754" point.

Btw. if we are worrying about the next `Float80` situation then this field does not need to be on the `protocol`, it can be on the type, remember that most of the time you use only 1 `Decimal` type in the whole app. We do not have `UInt80` (for `Float80`), but we have `UInt32`, `UInt64` and `UInt128`. For the `Decimal128` in the beginning it would be `UInt128` from the decimal package - maybe under some different name (`Decimal128.BitPattern`?) and without all of the `Int` operations (you do not need `zeroBitCount` etc.). At some point before the final release it would switch to `UInt128` from stdlib (if we ever get one).

This is exactly what `Double` does - in addition to `exponentBitPattern` and `significandBitPattern` required by `BinaryFloatingPoint` we have:

```swift
let d = Double(bitPattern: UInt64)
let bitPattern: UInt64 = d.bitPattern

// For Float80 it is not available:
Float80.nan.bitPattern (trigger code completion)
-> exponentBitPattern
-> significandBitPattern
```

Obviously if you want then you can add `associatedtype BitPattern: UnsignedInteger` (with/without `FixedWidthInteger`) to `DecimalFloatingPoint` protocol, just like oh-my-decimal. Though @scanon already addressed this:
> It does not, because FixedWidthInteger has all sorts of protocol requirements beyond being a bag of bits that can be used to build a decimal. There's no need to be able to divide bit patterns of decimal numbers, or count their leading zeros.
>
> Are those things easier to implement than decimal arithmetic? Yes. Does requiring that they be implemented impose some additional burden on the author of a decimal type? Also yes.

I'm 100% against:
> @xwu
>
> if the sign, raw exponent, and raw significand are each encodable and decodable (as they would be since they'd be of primitive types as per your link), then so too would be any type that's an aggregate of those three properties. In the simplest implementation, then, you would encode and decode a floating-point value in that manner.
>
> (…)
>
> This would also have the desirable (or, even essential) effect of allowing you to store bit patterns in any IEEE interchange format independent of what types are supported by the platform.

Storing `Decimal` as a separate sign, exponent, and significand is not space efficient. Also: why?

Combining the "sign, raw exponent, and raw significand" into a 128-bit pattern (most space efficient encoding) is way too complicated to put into the user-land. You need to know the right shifts, handle non canonical values, NaN payloads. On top of that the significand becomes extremely messy if you do not have `UInt128`.

I don't fully understand the 2nd paragraph. An example would be very helpful, it is very vague to the point that it says nothing.

- are we talking about the next `Float80` situation? The whole `#if (arch(i386) || arch(x86_64)) && !os(Windows) && !os(Android)`? Is there any practical example for `Decimal`?

- are we talking about situation similar to what @taylorswift described? I believe that this is a quite common scenario -> 2 people (me + @taylorswift) had the same problem and we came to the same conclusion. In this case you can just convert using `init`:

     ```swift
     // We have value in Decimal64
     let d64: Decimal64 = …
     // Our platform/database only supports Decimal128
     let d128 = Decimal128(d64) // Always exact because 128 > 64
     let bitPattern = d128.binaryEncoding // Or some other name
     ```

     If you want to manually change the decimal format then you have to re-bias the exponent, which is non-trivial because of overflows. Don't even think about writing converter to a smaller format outside of the `Decimal` package - way too complicated.

`Double` already has `bitPattern` property, so there is a precedence. It is just a matter of having `UInt128`. I would argue that there is a use case for having an access to the whole `bitPattern` of a `Decimal` type. It does not have to be on the `DecimalFloatingPoint` protocol, can be on type.


# Init And Conversion

## Inits

```swift
// Copy sign
init(signOf: Self, magnitudeOf: Self)
init(nan: BitPattern, signaling: Bool)

// Default on protocol:
init() {
  self = Self.zero
}
```

In `init(signOf:magnitudeOf:)` - what if `magnitudeOf` is not-canonical? Standard wants to make it canonical. Oh-my-decimal returns non-canonical (with the sign of `signOf`).

As for the `init(nan:signaling:)` the standard says:
> If G0 through G4 are 11111, then v is NaN regardless of S.
> Furthermore, if G5 is 1, then r is sNaN; otherwise r is qNaN.
>
> The remaining bits of G are ignored, and T constitutes the NaN’s payload,
> which can be used to distinguish various NaNs.
> The NaN payload is encoded similarly to finite numbers described below,
> with G treated as though all bits were zero. The payload corresponds to
> the significand of finite numbers, interpreted as an integer with a maximum
> value of 10^(3×J) − 1, and the exponent field is ignored (it is treated as
> if it were zero).
> A NaN is in its preferred (canonical) representation if the bits G6 through
> Gw + 4 are zero and the encoding of the payload is canonical.

This means following cases:
1. `payload` is already in canonical form -> ok.
2. `payload` is non-canonical (above `10^(3×J) − 1`), but it fits in `trailing significand` part of the encoding. Oh-my-decimal will accept this and return NaN with non-canonical payload. Tbh. `trailing significand` is quite arbitrary, for NaN you only need 1 sign bit + 6 NaN bits, everything else could be a payload.
3. `payload` does not fit inside `trailing significand` (which automatically makes it non-canonical). Oh-my-decimal will: `Precondition failed: NaN payload is not encodable.`.

Oh-my-decimal has very relaxed rules about the WRITING the payload: as long as you fit within `trailing significand` it will produce the value. I don't really want to crash, even though you are doing something that is a little bit weird. The check happens when READING the payload (for example: `String.init/totalOrder` functions), in which case we make the payload canonical (namely: `0`).

As for the @mgriebling implementation:

```swift
// mgriebling code
// https://github.com/mgriebling/DecimalNumbers/tree/main
public struct Decimal32 : Codable, Hashable {
  public init(nan payload: RawSignificand, signaling: Bool) {
    self.bid = ID.init(nan: payload, signaling: signaling)
  }
}

extension IntDecimal {
  public init(nan payload: RawSignificand, signaling: Bool) {
    let pattern = signaling ? Self.snanPattern : Self.nanPattern
    let man = payload > Self.largestNumber/10 ? 0 : RawBitPattern(payload)
    self.init(0)
    set(exponent: pattern<<(Self.exponentBits-6), sigBitPattern: man)
  }
}
```

So, the check also happens on the WRITE. And probably on the READ, but I have not checked this.

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

Oh-my-decimal returns unambiguous value in the following format: `[-][significand]E[signed exponent]`. Note that no cohort modification happens (`123E+2 == 12300E+0` but they are printed differently) and the exponent is always present even if it is `0`.

Swift probably also wants `NumberFormatter`.

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


# Math

## Unary

```swift
// Negate - on protocol
mutating func negate()

// Copy - default implementation
public static prefix func + (n: Self) -> Self {
  return n
}

// Copy-negate - default implementation
public static prefix func - (n: Self) -> Self {
  var copy = n
  copy.negate()
  return copy
}
```

What do we do if the value is not canonical?
Do we make it canonical or not?

For example: negation should ("flip the bit") OR ("flip the bit" AND make canonical)? Oh-my-decimal just flips the bit. Standard requires making it canonical.

Sign for `NaN` behaves just like sign for finite. This means that from oh-my-decimal pov the sign does not carry any data/information.

## Add

```swift
// Default rounding: toNearestOrEven
func adding(_ other: Self, rounding: DecimalFloatingPointRoundingRule, status: inout DecimalStatus) -> Self
func adding(_ other: Self, rounding: DecimalFloatingPointRoundingRule) -> Self
func adding(_ other: Self, status: inout DecimalStatus) -> Self
func adding(_ other: Self) -> Self

mutating func add(_ other: Self, rounding: DecimalFloatingPointRoundingRule, status: inout DecimalStatus)
mutating func add(_ other: Self, rounding: DecimalFloatingPointRoundingRule)
mutating func add(_ other: Self, status: inout DecimalStatus)
mutating func add(_ other: Self)

static func + (lhs: Self, rhs: Self) -> Self
static func += (lhs: inout Self, rhs: Self)
```

The most interesting edge cases for add/sub are:

1. special case when adding different signs (or subtracting same sign)

    ```swift
    // Decimal32 precision is 7.
    let lhs = Decimal32("1000000E8")!
    let rhs = Decimal32("5000001")!
    let result = lhs.subtracting(rhs, rounding: .toNearestOrAwayFromZero)
    print(result) // 9999999E+7
    ```

    Look closely at the numbers, this should NOT make sense. `rhs` is way smaller than `lhs`, it should round it back to `lhs` (we are well within `lhs.ulp/2 = 1E+8/2`), and yet apparently it didn't. The numbers that I used do contain a hint as to what is going on.

2. sign of exact `0`

    ```swift
    let lhs = Decimal32("123")!
    let rhs = Decimal32("123")!
    let result = lhs.subtracting(rhs, rounding: .down)
    print(result) // -0E+0
    ```

@mgriebling
Don't worry, your code handles them correctly giving:
1. `9.999999e+13`
2. `-0`

This is actually impressive.

## Sub

```swift
// Default rounding: toNearestOrEven
func subtracting(_ other: Self, rounding: DecimalFloatingPointRoundingRule, status: inout DecimalStatus) -> Self
func subtracting(_ other: Self, rounding: DecimalFloatingPointRoundingRule) -> Self
func subtracting(_ other: Self, status: inout DecimalStatus) -> Self
func subtracting(_ other: Self) -> Self

mutating func subtract(_ other: Self, rounding: DecimalFloatingPointRoundingRule, status: inout DecimalStatus)
mutating func subtract(_ other: Self, rounding: DecimalFloatingPointRoundingRule)
mutating func subtract(_ other: Self, status: inout DecimalStatus)
mutating func subtract(_ other: Self)

static func - (lhs: Self, rhs: Self) -> Self
static func -= (lhs: inout Self, rhs: Self)
```

## Mul

```swift
// Default rounding: toNearestOrEven
func multiplied(by other: Self, rounding: DecimalFloatingPointRoundingRule, status: inout DecimalStatus) -> Self
func multiplied(by other: Self, rounding: DecimalFloatingPointRoundingRule) -> Self
func multiplied(by other: Self, status: inout DecimalStatus) -> Self
func multiplied(by other: Self) -> Self

mutating func multiply(by other: Self, rounding: DecimalFloatingPointRoundingRule, status: inout DecimalStatus)
mutating func multiply(by other: Self, rounding: DecimalFloatingPointRoundingRule)
mutating func multiply(by other: Self, status: inout DecimalStatus)
mutating func multiply(by other: Self)

static func * (lhs: Self, rhs: Self) -> Self
static func *= (lhs: inout Self, rhs: Self)
```

## Div

```swift
// Default rounding: toNearestOrEven
func divided(by other: Self, rounding: DecimalFloatingPointRoundingRule, status: inout DecimalStatus) -> Self
func divided(by other: Self, rounding: DecimalFloatingPointRoundingRule) -> Self
func divided(by other: Self, status: inout DecimalStatus) -> Self
func divided(by other: Self) -> Self

mutating func divide(by other: Self, rounding: DecimalFloatingPointRoundingRule, status: inout DecimalStatus)
mutating func divide(by other: Self, rounding: DecimalFloatingPointRoundingRule)
mutating func divide(by other: Self, status: inout DecimalStatus)
mutating func divide(by other: Self)

static func / (lhs: Self, rhs: Self) -> Self
static func /= (lhs: inout Self, rhs: Self)
```

- `0 / finite = 0`
- `0 / 0 = nan + invalid operation`
- `finite / 0 = inf + divisionByZero`

There is an interesting part of the algorithm where you have to count trailing 0s of the result and possibly increase the exponent. Intel uses tables, but I went with manually unrolled binary search. We always divide by a power of 10 and with unrolling we can make them compile time constants, so the code generated by the compiler does not contain any divisions. At least that is what compiler explorer (godbolt.org) says.

`UInt64` can have at max 20 trailing zeros, so we have `⌈log2(20)⌉ = ⌈4.32…⌉ = 5` divisions. For `UInt128` it is `6`, because apparently this is how binary search works.

IDK, maybe tables are better.

## Remainder

```swift
func remainder(dividingBy other: Self, status: inout DecimalStatus) -> Self
func remainder(dividingBy other: Self) -> Self

mutating func formRemainder(dividingBy other: Self, status: inout DecimalStatus)
mutating func formRemainder(dividingBy other: Self)

func truncatingRemainder(dividingBy other: Self, status: inout DecimalStatus) -> Self
func truncatingRemainder(dividingBy other: Self) -> Self

mutating func formTruncatingRemainder(dividingBy other: Self, status: inout DecimalStatus)
mutating func formTruncatingRemainder(dividingBy other: Self)
```

No rounding and no operators!

Intel does not have `truncatingRemainder`, so we have to implement it ourself.

@mgriebling implementation:

```swift
// mgriebling code
// https://github.com/mgriebling/DecimalNumbers/tree/main

public struct Decimal32 : Codable, Hashable {
  public mutating func formTruncatingRemainder(dividingBy other: Self) {
    let q = (self/other).rounded(.towardZero)
    self -= q * other
  }
}
```

I have not checked this, but my intuition says that it may not be correct.

In oh-my-decimal:

```swift
extension DecimalMixin {

  internal func _remainder(dividingBy other: Self, status: inout DecimalStatus) -> Self {
    return self._remainder(dividingBy: other, status: &status, isNear: true)
  }

  internal func _truncatingRemainder(dividingBy other: Self, status: inout DecimalStatus) -> Self {
    return self._remainder(dividingBy: other, status: &status, isNear: false)
  }

  private func _remainder(
    dividingBy other: Self,
    status: inout DecimalStatus,
    isNear: Bool
  ) -> Self {
    (…)

    if isNear {
      Self._remRoundQuotientAwayFromZeroIfNeeded(
        sign: &sign,
        quotient: quotient,
        remainder: &remainder,
        rhsSignificand: rhsSignificand
      )
    }
  }
}
```

So both of the methods call the same function with `isNear: Bool` flag. This flag is checked in 2 places to potentially call `Self._remRoundQuotientAwayFromZeroIfNeeded`. Obviously at no point we actually calculate the proper `quotient`, there is no need for it. See the github repository for more details.

## Square root

```swift
// Default rounding: toNearestOrEven
func squareRoot(rounding: DecimalFloatingPointRoundingRule, status: inout DecimalStatus) -> Self
func squareRoot(rounding: DecimalFloatingPointRoundingRule) -> Self
func squareRoot(status: inout DecimalStatus) -> Self
func squareRoot() -> Self

mutating func formSquareRoot(rounding: DecimalFloatingPointRoundingRule, status: inout DecimalStatus)
mutating func formSquareRoot(rounding: DecimalFloatingPointRoundingRule)
mutating func formSquareRoot(status: inout DecimalStatus)
mutating func formSquareRoot()
```

How about adding `Int.squareRootFloor` to Swift Numerics? It is [important that this is `floor`](https://en.wikipedia.org/wiki/Integer_square_root). I'm sure that every programmer at some point had to write it.

Just last saturday (!) I was invited to collaborate (with commit access) on a Python repo regarding [Trouble-with-python3.12-function-sqrt](https://github.com/Baroudeme/Trouble-with-python3.12-function-sqrt/issues/1). Totally unknown person just inviting you to a repo with this exact problem! (My best guess is that this is some kind of recrutation tactic - programming interview 2.0. Please don't do this.)

In oh-my-decimal we have to implement it manually:
- `UInt32` -> from `Double`
- `UInt64` -> from `Double ±1` for correction
- `UInt128` -> Newton + `log2` estimation
- `UInt256` (yes, we have this type, don't ask) -> Newton + `log2` estimation (same code as `UInt128`)

## FMA

```swift
// Default rounding: toNearestOrEven
func addingProduct(
  _ lhs: Self,
  _ rhs: Self,
  rounding: DecimalFloatingPointRoundingRule,
  status: inout DecimalStatus
) -> Self
func addingProduct(_ lhs: Self, _ rhs: Self, rounding: DecimalFloatingPointRoundingRule) -> Self
func addingProduct(_ lhs: Self, _ rhs: Self, status: inout DecimalStatus) -> Self
func addingProduct(_ lhs: Self, _ rhs: Self) -> Self

mutating func addProduct(
  _ lhs: Self,
  _ rhs: Self,
  rounding: DecimalFloatingPointRoundingRule,
  status: inout DecimalStatus
)
mutating func addProduct(_ lhs: Self, _ rhs: Self, rounding: DecimalFloatingPointRoundingRule)
mutating func addProduct(_ lhs: Self, _ rhs: Self, status: inout DecimalStatus)
mutating func addProduct(_ lhs: Self, _ rhs: Self)
```

I'm not the biggest fan of how FMA works in Swift, I would rather see a `static` method. The 1st instinct is to look for `fusedMultiplyAdd` and that gives nothing in code completion.

Anyway… it is FMA, so I will not even list all of the possible edge cases. I can vouch for [Hossam A. H. Fahmy test suite](http://eece.cu.edu.eg/~hfahmy/arith_debug/). Those tests are not exhaustive, but they are waaaay better than anything that I could ever create.

Be prepared that writing `fma` will also force re-write of `add`. In oh-my-decimal from certain point almost everything is shared - this makes `add` more complicated than it needs to be.

\<rant\>

Implementing FMA is such a massive waste of time. Oh-my-decimal code is so complicated that I'm sure that there is a bug somewhere. The best thing is that this method is quite useless on `Decimal`, because most of the time you want a separate `mul` and `add`. I may be wrong but `Foundation.Decimal` does not even have it.

But standard requires it, and so does `FloatingPoint` protocol. So, good luck to whoever is going to implement it. I'm just happy that this is not me. I already suffered enough.

\</rant\>


# Compare And Hash

## Equatable, comparable

```swift
func isEqual(to other: Self, status: inout DecimalStatus) -> Bool
func isEqual(to other: Self)

func isLess(than other: Self, status: inout DecimalStatus) -> Bool
func isLess(than other: Self)

func isLessThanOrEqualTo(_ other: Self, status: inout DecimalStatus) -> Bool
func isLessThanOrEqualTo(_ other: Self)

static func == (lhs: Self, rhs: Self) -> Bool { lhs.isEqual(to: rhs) }
static func < (lhs: Self, rhs: Self) -> Bool { lhs.isLess(than: rhs) }
static func <= (lhs: Self, rhs: Self) -> Bool { lhs.isLessThanOrEqualTo(rhs) }
static func > (lhs: Self, rhs: Self) -> Bool { rhs.isLess(than: lhs) }
static func >= (lhs: Self, rhs: Self) -> Bool { rhs.isLessThanOrEqualTo(lhs) }
```

You only need to implement those (maybe without the `status` if you do not have it):

```swift
func isEqual(to other: Self, status: inout DecimalStatus) -> Bool
func isLess(than other: Self, status: inout DecimalStatus) -> Bool
func isLessThanOrEqualTo(_ other: Self, status: inout DecimalStatus) -> Bool
```

Almost everything is defined in the standard:
- `+0 == -0` for any sign and exponent.
- different cohorts of the same value are equal.
- non-canonical values should be equal to `±0`.
- `NaNs` are never equal.
- etc…

Side note: for compare operations you want to read standard 2019 instead of 2008. The content is the same, but the language is more approachable.

Oh-my-decimal implements `compareQuiet` from the standard. `compareSignaling` is just a tiny modification of `compareQuiet` which can be added in `extension` if user so desires. IIRC, standard actually recommends to use `compareSignaling` for operators, or something like that… but whatever. It doesn't matter…

Under the hood oh-my-decimal has:

```swift
internal enum CompareResult {
  case nan
  case less
  case equal
  case greater
}

extension DecimalMixin {
  internal static func _compare(_ x: Self, _ y: Self) -> CompareResult { … }
}
```

This is enough to implement all of the equal/compare/min/max/totalOrder operations.

## Hashable

Using float as a `dict` key or an element in `set` is a little bit weird, but I can image some use cases.

There is a potential attack vector for certain dictionary implementations where you pack them with `NaN`. `NaNs` are never equal to anything, so things would go in, but never get out. This could bring overall performance to `O(n)`.

As for the @mgriebling implementation:

```swift
// mgriebling code
// https://github.com/mgriebling/DecimalNumbers/tree/main
public struct Decimal32 : Codable, Hashable {
  typealias ID = IntDecimal32
  var bid = ID.zero(.plus)
}

struct IntDecimal32 : IntDecimal {
  typealias RawData = UInt32
  var data: RawData = 0
}

protocol IntDecimal : Codable, Hashable {}
```

So, it seems that `func hash(into hasher: inout Hasher)` is not redefined.
This means that Swift compiler will just hash all of the stored properties which in this case is `var data: UInt32` representing `BID`.

Hmm… this depends on how you define equality (equality and hash have to be in sync). You can do this if your equality is also defined by `bid` equality.

Oh-my-decimal uses IEEE notion of equality, so the implementation is a little bit longer. In fact it is too long to put into this post, so check the github repository.

Bonus points for `hash(0)` always being the same for any sign and exponent. Finite non canonical also need to return the same value as `hash(0)` - they are equal.

## Min/max

```swift
static func minimum(_ x: Self, _ y: Self, status: inout DecimalStatus) -> Self
static func minimum(_ x: Self, _ y: Self) -> Self

static func maximum(_ x: Self, _ y: Self, status: inout DecimalStatus) -> Self
static func maximum(_ x: Self, _ y: Self) -> Self

static func minimumMagnitude(_ x: Self, _ y: Self, status: inout DecimalStatus) -> Self
static func minimumMagnitude(_ x: Self, _ y: Self) -> Self

static func maximumMagnitude(_ x: Self, _ y: Self, status: inout DecimalStatus) -> Self
static func maximumMagnitude(_ x: Self, _ y: Self) -> Self

// === Examples ===

// Standard: canonicalized number
// Swift: number
print(Decimal64.minimum(Decimal64.nan, 1, status: &status)) // 1E+0 🟢
print(Double.minimum(Double.nan, 1)) // 1.0 🟢

// Standard: nan + invalidOperation
// Swift: number
print(Decimal64.minimum(1, Decimal64.signalingNaN, status: &status)) // nan + invalidOperation 🟢
print(Double.minimum(1, Double.signalingNaN)) // 1.0 🔴
```

We have the following options:

1. standard 2008 - this is what oh-my-decimal implements
    > `sourceFormat minNum(source, source)`
    >
    > `minNum(x, y)` is the canonicalized number `x if x < y, y if y < x`, the canonicalized number if one operand is a number and the other a quiet NaN. Otherwise it is either x or y, canonicalized (this means results might differ among implementations). When either x or y is a signalingNaN, then the result is according to 6.2.

2. standard 2019 - new operations as there was [a whole debate](https://grouper.ieee.org/groups/msc/ANSI_IEEE-Std-754-2019/background/minNum_maxNum_Removal_Demotion_v3.pdf) about the corner cases of 2008
    > `sourceFormat minimum(source, source)` <--- THIS ONE!!1<br/>
    >
    > `minimum(x, y)` is `x if x<y, y if y<x`, and a quiet NaN if either operand is a NaN, according to 6.2. For this operation, `-0` compares less than `+0`. Otherwise (i.e., when `x=y` and signs are the same) it is either x or y.
    >
    > ---
    >
    > `sourceFormat minimumNumber(source, source)`
    >
    > `minimumNumber(x, y)` is `x if x<y, y if y<x`, and the number if one operand is a number and the other is a NaN. For this operation, `-0` compares less than `+0`. If `x=y` and signs are the same it is either x or y. If both operands are NaNs, a quiet NaN is returned, according to 6.2. If either operand is a signaling NaN, an invalid operation exception is signaled, but unless both operands are NaNs, the signaling NaN is otherwise ignored and not converted to a quiet NaN as stated in 6.2 for other operations.

3. current Swift behavior
   - [Swift documentation](https://developer.apple.com/documentation/swift/double/minimum(_:_:)) links to the standard 2008 and quotes:
      > If both x and y are NaN, or either x or y is a signaling NaN, the result is NaN
   - in practice for `sNaN` it returns the non-NaN operand (see code example above)

Agner Fog blog has a [good summary](https://www.agner.org/optimize/blog/read.php?i=1012):
> An important change is that the minimum and maximum functions are changed so that they are sure to propagate NANs, while the 2008 version made the illogical decision that minimum and maximum should return a non-NAN if one of the inputs is a NAN and the other is a non-NAN number. I would like to see this change implemented in new hardware instructions. The current implementation of min and max in SSE and later instruction sets are conforming neither to the 2008 standard nor to the new 2019 standard. Instead, minps(A,B) is equivalent to A < B ? A : B, and maxps(A,B) is equivalent to A > B ? A : B. These functions will return B if A or B is a NAN because all comparisons with a NAN return false.

I think that standard 2019 `minimum(x, y)` is the most logical option, but this is not how `Swift.Double` behaves. Oh-my-decimal went with standard 2008. I can't say that I'm perfectly happy with it

## Total order

```swift
func isTotallyOrdered(belowOrEqualTo other: Self) -> Bool

// In protocol extension:
func isMagnitudeTotallyOrdered(belowOrEqualTo other: Self) -> Bool {
  let s = self.magnitude
  let o = other.magnitude
  return s.isTotallyOrdered(belowOrEqualTo: o)
}
```

`Double` does not have `isMagnitudeTotallyOrdered`. Since sign for the `Decimal` is implemented in software (and thus behaves predictably) we can have the default implementation.


# Operations

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

## Next

```swift
var nextDown
func nextUp(status: inout DecimalStatus) -> Self

var nextUp: Self
func nextDown(status: inout DecimalStatus) -> Self
```

…

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

## Round

```swift
// Default rounding: .toNearestOrAwayFromZero
func rounded(_ rule: DecimalFloatingPointRoundingRule, status: inout DecimalStatus) -> Self
func rounded(_ rule: DecimalFloatingPointRoundingRule) -> Self
func rounded(status: inout DecimalStatus) -> Self
func rounded() -> Self

mutating func round(_ rule: DecimalFloatingPointRoundingRule, status: inout DecimalStatus)
mutating func round(_ rule: DecimalFloatingPointRoundingRule)
mutating func round(status: inout DecimalStatus)
mutating func round()
```

In standard we have:

> ― sourceFormat roundToIntegralExact(source)<br/>
> Rounds x to an integral value according to the applicable rounding-direction attribute. Will raise inexact.
>
> ― sourceFormat roundToIntegralTiesToEven(source)<br/>
> ― sourceFormat roundToIntegralTiesToAway(source)<br/>
> ― sourceFormat roundToIntegralTowardZero(source)<br/>
> ― sourceFormat roundToIntegralTowardPositive(source)<br/>
> ― sourceFormat roundToIntegralTowardNegative(source)<br/>
> (Later in: 5.9 Details of operations to round a floating-point datum to integral value)<br/>
> For the following operations, the rounding direction is specified by the operation name and does not depend on a rounding-direction attribute.
> These operations shall not signal any exception except for signaling NaN input.

Oh-my-decimal has `roundToIntegralExact` (the one with `isInexact`). But if you do not have `DecimalStatus` then I do not think there is any difference.

Apart from this… eee… nothing interesting?


# Other

## Swift evolution

Where do we put `Decimal`?
- stdlib - this way we would have `Float/Double` and `Decimal` in the same place which makes sense given how "symmetrical" those types are - same thing different radix.

  This would also allow us to place `Decimal` in the Swift book in the [Floating-Point-Numbers](https://docs.swift.org/swift-book/documentation/the-swift-programming-language/thebasics#Floating-Point-Numbers) section. This could ease the confusion the new programmers face: how to represent money? Hmm… the Swift book mentioned:

  > Floating-point numbers are numbers with a fractional component, such as 3.14159, 0.1, and -273.15.
  >
  > (…)
  >
  > In situations where either type would be appropriate, `Double` is preferred.

  Oh! Yes! `Double` is probably the right choice!

  Anyway, if we want `Decimal` in stdlib then it has to go through Swift evolution. Not having `UInt128` could be a certain problem, because I am almost 100% sure that the `Decimal128` would need to expose some property with this type.

  We may want to add `typealias Float64 = Double`. There was a discussion about this on this forum, a few people from this thread also participated in it.

- Foundation - I don't see the reason why . As far as I know the new Foundation design does not contain it.

- Swift Numerics - I see it as more of a "staging" environment where work on with it before moving to stdlib.

- separate repo - oh-my-decimal contains a lof of the supporting infra (Python scripts, code generators, test suites etc.). I assume this would also be true for the official `Decimal` type. A separate "staging" (before stdlib) repo may be better, because you do not have to worry about the other Swift Numerics thingies.

## Transcendental functions

Oh-my-decimal does not implement any transcendentals. `Decimal.pow(exponent: Int)` may be useful, but it is not a must-have.

## Exists?

@scanon @xwu
If I were tasked with designing `FloatingPoint/BinaryFloatingPoint` protocols I would also do a rough sketch for `DecimalFloatingPoint` to decide what goes to `FloatingPoint` and what goes to `BinaryFloatingPoint/DecimalFloatingPoint`. Does such document exist at Apple? Can it be made public?

## Google summer of code

I'm not really sure if `Decimal` is the best project GSOC.

`Decimal` is all about the precision, so writing it takes more time than usual code. In practice you can't write a decimal without bugs:
-  [Hossam A. H. Fahmy tests](http://eece.cu.edu.eg/~hfahmy/arith_debug/) found bugs in (taken from their website):
   - decimal64 and decimal128 designs of SilMinds
   - FMA and Sqrt operations of decNumber developed by Dr. Mike Cowlishaw. This is the same Mike Cowlishaw who was an editor of standard 2008 and the person responsible for [speleotrove.com/decimal](https://speleotrove.com/decimal/).
   - FMA for decimal128 in the Intel library by Dr. Marius Cornea
- Intel still has errors in tests:
  - few lines with invalid result
  - few lines that work, but have incorrect format: missing expected `status`, `next` is a binary operation etc.
- even [Hossam A. H. Fahmy tests](http://eece.cu.edu.eg/~hfahmy/arith_debug/) have 1 incorrect FMA line
- oh-my-decimal - I wrote this -> it is bad

Also, `Decimal` requires an enormous amount "warm up" time before you have something to show:
- reading and understanding standard - this is non-trivial, because most programmers are not accustomed to thinking in IEEE 754 - the standard was designed to "just work" in most common cases.
- designing protocol/types - this is what this thread is all about
- getting accustomed to how decimal arithmetic works - mostly playing with Intel library, there are a few surprises
- (maybe) writing a wrapper for Intel lib - this is how oh-my-decimal started. I would highly recommend this approach, because you can just port up to the next `return` statement.

All that would probably use half of the time, and we have not even started writing the actual implementation.

But wait! We forgot about something! Tests! Oh-my-decimal has:
- [Intel tests](https://www.intel.com/content/www/us/en/developer/articles/tool/intel-decimal-floating-point-math-library.html) - Python script generates Swift unit tests.
- [Speleotrove tests](https://speleotrove.com/decimal/) - Python script generates Swift unit tests.
- [Hossam A. H. Fahmy tests](http://eece.cu.edu.eg/~hfahmy/arith_debug/)
- [oh-my-decimal-tests](https://github.com/LiarPrincess/Oh-my-decimal-tests) - tests generated using Python `decimal` module
- unit tests written by hand - they still take a few days to write

But don't despair!

…

Yet.

…

How about:
- you can't just write `Decimal` according to the standard, it has to work similar to `Swift.Double` because this is what users expect.
- writing your own `UInt128` - `DoubleWidth` from SwiftNumerics [crashes or gives incorrect results](https://github.com/apple/swift-numerics/issues/272). Oh-my-decimal also has `UInt256`, you can write `Decimal` without it but it would much more difficult. For FMA you may need `3x bitWidth` (`UInt96`, `UInt192`, `UInt384`).
- compiler bugs - compiling arrays with 1000 elements (`UInt256`) should not take 15 min and 20GB of ram. Thb. I never managed to finish this build. I decided to split those tables with Python script.

That's a sizeable number of tasks. And you are working with a person with whom you have never worked before. I also saw that some of the possible participants had no Swift experience, so that would add more time. I know that a lof of people would help the student, and the scope can be reduced to: properties, `+`, `-`, `*`, `/`, `reminderNear`, `quantization`, `compare` (definitely not FMA or binary floating point interop), but…

Having written `Decimal` and [BigInt](https://github.com/LiarPrincess/Violet) ([twice](https://github.com/LiarPrincess/Violet-BigInt-XsProMax)) I think that `BigInt` is more suitable for GSOC. It is easier and more self-contained (meaning that when you finish a certain part you know that it mostly works, while in `Decimal` it is more of a "how many bugs are there"). You could for example:
- 2 weeks - setup/design/discussions
- 4 weeks - implementation - most basic version. Just the school math, not Karatsuba etc.
- 3 weeks - writing tests + some basic performance tests
- 3 weeks - one of:
  - performance improvements to basic operations
  - implementation of 1 advanced mul/div algorithm

I think that `BigInt` is just easier to introduce to a new person, most of the time they already know what to do. Though the question would be: which one is more needed?

## @mgriebling

### Intel unit tests

I see that you use [an array of test cases](https://github.com/mgriebling/DecimalNumbers/blob/b223205904f06d0e4056a87e5c86e61a10737f5d/Tests/DecimalNumbersTests/Decimal32Tests.swift#L99) and execute them as 1 unit test.

Oh-my-decimal uses a Python script to transform Intel tests into Swift unit tests. This way you have more tooling support, and you can execute tests in parallel which makes them faster.

### Tables

> @mgriebling wrote:
>
> Intel's goal was to use copy & paste as much as possible. :wink: They also have lots of hardcoded numbers and obscure look-up tables, many of which have been replaced.

It is a truth universally acknowledged, that tables "do not scale" in generic contexts. Though I would still try to use them as much as possible.

For example in power of 10 you have (quick note: this and `DecimalDigitCount` are 2 most used tables):

```swift
// mgriebling code
// https://github.com/mgriebling/DecimalNumbers/tree/main

/// Returns ten to the `i`th power or `10^i` where `i ≥ 0`.
static func power10<T:FixedWidthInteger>(_ i:Int) -> T { _power(T(10), to:i) }

func _power<T:FixedWidthInteger>(_ num:T, to exp: Int) -> T {
  // Zero raised to anything except zero is zero (provided exponent is valid)
  guard exp >= 0 else { return T.max }
  if num == 0 { return exp == 0 ? 1 : 0 }
  var z = num
  var y : T = 1
  var n = abs(exp)
  while true {
    if !n.isMultiple(of: 2) { y *= z }
    n >>= 1
    if n == 0 { break }
    z *= z
  }
  return y
}
```

While oh-my-decimal uses tables:

```swift
extension Tables {

  /// Usage: `let pow10: UInt64 = Tables.getPowerOf10(exponent: 3)`.
  internal static func getPowerOf10<T: FixedWidthInteger>(exponent index: Int) -> T {
    assert(index >= 0, "Negative exponent in pow10?")

    if index < data128.count {
      let r = data128[index]
      assert(r <= T.max)
      return T(truncatingIfNeeded: r)
    }

    let index256 = index - data128.count
    let r = data256[index256]
    assert(r <= T.max)
    return T(truncatingIfNeeded: r)
  }
}
```

I think it boils down to performance, but I have not measured it:
- If you have a single decimal operation then manual calculation may be faster, because table lookup may miss cache. But single decimal operation will rarely be a performance problem, you clearly do not do enough calculations for this to matter.
- If you have multiple decimal operations (in a loop etc.) then tables may be faster because lookups will be fast. For example if we need to call `Tables.getPowerOf10(x)` 1000 times then manual calculation will re-calculate similar numbers over and over again, and multiplication is quite expensive operation.

Btw. I think that Intel code is generated - nobody wants to write the same thing 3 times, especially when dealing with such a precise code. They probably have 1 abstract decimal and they generate code 3 times for different formats.

### bid_factors

```swift
// mgriebling code
// https://github.com/mgriebling/DecimalNumbers/tree/main

/// Table of division factors of 2 for `n+1` when `i` = 0, and factors of 5
/// for `n+1` when `i` = 1 where 0 ≤ `n` < 1024. When both are factors,
/// return divisors of both are combined.  For example when `n` = 19, `n+1`
/// or 20 is a factor of both 2 and 5, so the return for `i=0` is 2 (not 4),
/// and `i=1` is 1.  This function reproduces the contents of the table
/// `bid_factors` in the original.
static func bid_factors(_ n:Int, _ i:Int) -> Int {
  var n = n + 1
  if i == 0 && n.isMultiple(of: 2) {
    var div2 = 1
    n /= 2
    while n.isMultiple(of: 5) { n /= 5 } // remove multiples of 5
    while n.isMultiple(of: 2) { div2 += 1; n /= 2 }
    return div2
  } else if i == 1 && n.isMultiple(of: 5) {
    var div5 = 1
    n /= 5
    while n.isMultiple(of: 2) { n >>= 1 }
    while n.isMultiple(of: 5) { div5 += 1; n /= 5 }
    return div5
  }
  return 0
}
```

I'm not sure if you have to divide by the other factor. 2 and 5 are relatively prime, so if you do factorization (Wikipedia calls it [fundamental theorem of arithmetic
](https://en.wikipedia.org/wiki/Fundamental_theorem_of_arithmetic); such a posh name) then they will be in "separate buckets". I have not tested this. Oh-my-decimal uses tables.


