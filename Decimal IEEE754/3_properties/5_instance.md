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
