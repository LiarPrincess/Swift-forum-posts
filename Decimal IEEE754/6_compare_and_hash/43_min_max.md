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
