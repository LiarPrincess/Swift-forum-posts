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
