## Ergonomic & documentation

Though, by far my biggest gripe with the proposal is (btw. we are 25k characters in):
- we have 6 overloads with 8 or 9 arguments each.
- all of the overloads start with the same arguments making it hard to see the difference
- some of the arguments are optional which basically mean more overloads.

This makes the code completion for `Subprocess.run(` useless.

Also, the documentation would be very long - around 50% of the proposal. We would require people to spend 20min on reading before they can use the API. Then they would use it and come back to the documentation to re-read it because there is no "progressive disclosure". There is just 1 method with multiple overloads.

Also, we have to attach (almost) the same documentation to each `run` overload. And given that most of the stuff is the same (prolog and everything from `Executable` up to `PlatformOptions` arguments) it will be hard for users to differentiate between different overloads.

To solve this we would put the documentation on the `Subprocess` type, but still it will be ~50% of the proposal with multiple paragraphs. You can't create link to a paragraph to help somebody on Stack Overflow.

Also, API is different from other systems/languages. You can't just google "linux kill process" because most of this is not applicable to the model presented in the proposal.

I like the [old Foundation Process docs](https://developer.apple.com/documentation/foundation/process). They are way too short, but when I want to read about something I just click it in the left side-bar.

---

That's theory, in practice:

![code-completion-for-many-run-methods](img_quiz_1.jpg)

Q1: Which overload should we choose if we want to run `git status`?

```swift
let result = try await Subprocess.run(executing: .at("ls"))
```

Q2: Which `run` overload will this call? Will this open pipes for communication? Will this allocate buffer to collect output?

---

Answer 1: None of them. You have to copy an example from the documentation. Maybe if you are familiar with the API you just select randomly and remove all of the arguments you do not need. This is a bit of a made up scenario, because new users will never type `Subprocess.run(` they will try the initializer `Subprocess(` first, and then go to docs without trying anything else.

Answer 2: No closure -> this is `CollectedResult` call with `.noInput`. It will allocate buffers, so if this is not what you want then you just wasted some memory. Btw. there is a bug in the question that I asked: it should be `.named("ls")`. I think `.atPath("ls")` would make it easier to spot. Though it is still weird to read:

  ```swift
  // Executing what? The subject is missing.
  Subprocess.run(executing: .named("ls"))
  // Proper sentence, but nobody is going to write it this way.
  // In Poland we say: butter is butterish.
  // It means: padding to make an essay longer just to pass length requirement.
  Subprocess.run(executing: Executable.named("ls"))
  // Different label.
  Subprocess.run(executable: .named("ls"))
  ```
