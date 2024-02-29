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
