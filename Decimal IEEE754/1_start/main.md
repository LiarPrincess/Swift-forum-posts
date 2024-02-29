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
