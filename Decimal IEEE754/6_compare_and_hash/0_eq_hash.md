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
