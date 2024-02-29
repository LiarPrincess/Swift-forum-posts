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
