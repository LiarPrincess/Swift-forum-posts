# Fin

With all that it is clear that the community should drop everything, cancel WWDC and start implementing a good `BigInt`.

Please don't.

At least I don't think this a good idea. I have never used `BigInt` in a business scenario, and a lot of the programs that use it are artificial Fibonacci-like benchmarks. There are some real-world use cases, but they can be solved with GMP.

[quote="taylorswift, post:44, topic:71583"]
i think the focus on BigInt in this thread is illustrative because in the past at a different company i recall experiencing similar difficulties with underdeveloped libraries and being blocked by things like [IEEE decimal support](https://en.wikipedia.org/wiki/Decimal128_floating-point_format) or [ION support](https://github.com/amazon-ion).
[/quote]

☝️⬆️🆙📤🔺👆 the decimal thingie.

Support for IEEE 754 decimal sucks across the board, not only in Swift.
- [Intel library](https://www.intel.com/content/www/us/en/developer/articles/tool/intel-decimal-floating-point-math-library.html) should work as long as you are on supported platform and can FFI to C
- C folks are [working on it](https://en.cppreference.com/w/c/compiler_support/23)
- (as you pointed out in another thread) Mongo supports it as `Decimal128` via `BID`.

Anyway, for my needs [I implemented it myself](https://github.com/LiarPrincess/Oh-my-decimal), and now I diligently ignore 70% of the library, because only `+-*/`, `truncatingRemainder` and `quantize` are useful.



