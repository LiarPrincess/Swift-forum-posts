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
