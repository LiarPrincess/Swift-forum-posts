
## IO - Default values

In proposal we have:

```swift
public static func run<R>(
  …,
  input: InputMethod = .noInput,
  output: RedirectedOutputMethod = .redirect, // <-- here
  error: RedirectedOutputMethod = .discard,
  _ body: (@Sendable @escaping (Subprocess) async throws -> R)
) async throws -> Result<R>
```

`redirect` will create pipe. If the user forgets to read it (or they are not interested) we may deadlock when pipe buffer becomes full. Isn't `discard` a better **default** value?

```swift
let example1 = try await Subprocess.run(
  executing: .named("ls")
) { … }

let example2 = try await Subprocess.run(
  executing: .named("ls"),
  output: .redirect
) { … }
```

In `example2` you can clearly see that something is happening. The framework did not decide this for us. It was our own decision, and it is very visible to the readers.

Btw. `discard` writes to `/dev/null`. As far as I know you can get away with only 1 discard file with `O_RDWR`. This way you use less resources. May matter on servers.

## AsyncBytes - Optional output props

```swift
public struct Subprocess: Sendable {
  public var standardOutput: AsyncBytes?
  public var standardError: AsyncBytes?
}
```

Those properties are only usable if we specified `.redirect`. Why does the positive path require optional unwrap with `!`?

```swift
try await Subprocess.run(
  executing: .named("ls"),
  output: .redirect
) { process in
  process.standardOutput!.<something>
}
```

This `!` is not needed. `AsyncBytes` should store `FileDescriptor?` and throw `EBADF` (or `precondition`) if we try to use it when the argument was not `.redirect`.


## AsyncBytes - Read buffer

```swift
public struct AsyncBytes: AsyncSequence, Sendable {
  public typealias Element = UInt8
  public typealias AsyncIterator = Iterator

  public func makeAsyncIterator() -> Iterator
}
```

The only thing we have here is `AsyncIterator`. What if I wanted to write a `StringOutput` type that deals with all of the `String` stuff in a Java style decorator fashion:

```swift
let stdout = StringOutput(process.standardOutput!, encoding: .utf8)

for await line in stdout.lines() {
  …
}
```

I'm sure everybody knows how `StringOutput` internals would look like.

Why do I need to read byte-by-byte? Can't I just read the whole buffer of data? This just forces me to write the code that undoes what `AsyncBytes` did. It applies an abstraction (including its own buffering) that I have not asked for. And now we need 2 buffers: `AsyncBytes` one and the one where I gather my `String`.


## StandardInputWriter - Call `finish`?

For `StandardInputWriter` proposal states:

> **Note**: Developers must call `finish()` when they have completed writing to signal that the standard input file descriptor should be closed.

Why?

We are basically racing the process against the user code (`body` argument).
- process finishes 1st - reading end of the pipe is closed -> `SIGPIPE/EPIPE`, but this has nothing to do with closing the file
- user code (`body`) finishes 1st - can't we close it after? If the process is still running then it will get values from the buffer, and eventually `read(…) == 0`

I guess in theory we could have a subprocess that reads from the `stdin` in a loop, so if we do not close the pipe it will loop forever. But for this use case we require **all** of the users to call `finish()`?

Why is it called `finish` instead of `close`?

Why can't the `Subprocess` own the input? Is there any situation where the input outlives the `Subprocess`?

We could [make it idempotent](https://github.com/LiarPrincess/Vampires-and-sunglasses/blob/main/Sources/Lib/Subprocess%2BIO.swift#L30) where the 1st close would set the `FileDescriptor` to `nil` (to prevent double-closing). Then the `Subprocess` would call `close` again, just in case the user forgot. This will make `finish/close` optional for the users. They can, but they do not have to.

I do not like APIs based on the "user has to remember to do X". At least back in the `RxSwift` times we had `DisposableBag` and forgetting about it was a compiler warning. Here we get nothing.

## StandardInputWriter - Sendable args?

```swift
public struct StandardInputWriter: Sendable {

  private let actor: StandardInputWriterActor

  @discardableResult
  public func write<S>(_ sequence: S) async throws -> Int where S : Sequence, S.Element == UInt8

  @discardableResult
  public func write<S: AsyncSequence>(_ asyncSequence: S) async throws -> Int where S.Element == UInt8
}
```

Those `Sequences` will go to the `actor`. Shouldn't they be `Sendable`? I get concurrency warning for `try await Array(asyncSequence)`.

I think that any green-field project should [enable `StrictConcurrency` by default](https://github.com/LiarPrincess/Vampires-and-sunglasses/blob/main/Package.swift#L34). People may say something about false-positives, or that this feature is not yet ready. For me it caches bugs. And it creates the right mental model of how things work, so that we do not have to "unlearn" later.

## IO - StandardInputWriter - `write` names

Bike-shedding: on `FileDescriptor` methods that take `Sequence` are called `writeAll`. On `StandardInputWriter` (which is a wrapper around a `FileDescriptor`) we have `write`.

Do we want more consistent naming?
