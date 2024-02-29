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
