In the old thread I wrote a [long post](https://forums.swift.org/t/pitch-swift-subprocess/69805/53) about some issues that I see in the proposal. I think most of the problems there are still relevant, so I would love to see them discussed here.

This post works differently. Each section starts with a `Subprocess.run` snippet that will do one of:
- crash child
- crash parent
- deadlock child-parent
- deadlock parent
- make Swift Concurrency inoperable

This is going to be a long one, but you can run all of the code examples by yourself. "Pride and Prejudice.txt" is available at Project Gutenberg. Ubuntu 22.04.4 LTS, should work on macOS (it is actually even easier to deadlock there).

## `Collected` - `limit` deadlocks

```swift
try await Subprocess.run(
  executing: .at(FilePath("\(bin)/cat")),
  arguments: ["Pride and Prejudice.txt"]
)

print("after")
```

**Expected:** prints "after"

**Result:**
- nothing is printed
- it seems to be hanging
- `cat` is visible in System Monitor even after a few minutes; deadlock

If we open in in the debugger we will see that it hangs on:

```swift
internal func captureStandardError() throws -> Data? {
  guard case .collected(let limit, let readFd, _) = self.executionError else {
    return nil
  }
  let captured = try readFd.read(upToLength: limit) // <-- here; limit is 131072
  return Data(captured)
}
```

This is a blocking `FileDescritor.read` on a cooperative thread. It should not deadlock, because when the `cat` finishes it should just resume. (That said, a blocking read would not be my 1st choice in this case.)

The culprit is somewhere else. As it turns out the `limit` that we specify does not only regulate the amount of bytes that we care about, but also sets an indirect limit on how much the process can write in total:

- `stdout <= limit` - 🟢 ok
- `stdout <= limit + pipe size` - 🟢 ok, but the output is truncated
- `stdout > limit + pipe size` - 🔴 deadlock

Am I the only one surprised by it? When I read the proposal I though of: `git status limit(500)` will just take the first 500 bytes of the output and forget about the rest. But it turns out that "the rest" is critical, as it decides about the deadlock.

And remember that we have to set a limit. Either directly via the `collect(limit: Int)` or indirectly via `collect`. That said the proposal says: "By default, this limit is 16kb", but in code we have `.collected(128 * 1024)`. So, to get 16kb I have to specify `128 * 1024` as an argument. What is the unit?

How about using `Int.max` as a limit? Or `Int.min`? Or `-1`? All will crash with `SIGILL`: illegal instruction operand. The code in PR will actually try to allocate `Int.max` of memory:

```swift
extension FileDescriptor {
  internal func read(upToLength maxLength: Int) throws -> [UInt8] {
    let buffer: UnsafeMutableBufferPointer<UInt8> = .allocate(capacity: maxLength)
    let readCount = try self.read(into: .init(buffer))
    let resizedBuffer: UnsafeBufferPointer<UInt8> = .init(start: buffer.baseAddress, count: readCount)
    return Array(resizedBuffer)
  }
}
```

But what if we guess the total size of the `stdout` wrong? It not only deadlocks, but also takes 2 cooperative threads with it: the `read(stderr)` one and the `waitpid` one.

The conditions for a deadlock are:
- we have a "chatty program" - it prints a lot
- we underestimated the output by pipe buffer size

Enter… the Swift compiler. It is a chatty program, and immediately upon seeing the proposal I thought of:
1. git clone
2. cd
3. swift build

The standard CI stuff. This will work… for a while. But then our app will grow bigger: we will add dependencies, we will add more `.swift` files, and it will cross the max `stdout` and deadlock. If this does not convince you then just use `swift test`, this will 100% deadlock after a few weeks.

But you can always cancel the `Task` which will kill the process and reclaim the cooperative threads! No, you can't. It is a race condition. Going back to our CI example: lets say we implement a monitor in Swift that will `kill` the `Process/Task` after 30 min (seems like a reasonable upper bound for most of the `swift build` uses). What if during those 30 min users submitted enough builds to choke the Swift concurrency? Will the Monitor work correctly?

The only *reliable* way to find out about this is from the external sources. Maybe the row in the database did not appear? Maybe the users are frustrated that the CI is not working? Etc.

Also, look how easy this was! I just used `swift build`. No maliciously crafted arguments. No specially prepared programs. Everything with default values, and it deadlocked. Where does this put our user? Do they know what went wrong? Do they have some information? Can they at least link this with `stdout`? No.

In the long post in the pitch thread I proposed changing the defaults to: `input: .noInput` and `output: .discard` for this exact reason. At least it will not deadlock. To deadlock they have to explicitly set the `output: .collect(limit: …)`, which is more visible. I had a discussion about this with @wadetregaskis, and their stance is (I cropped it to save space, please go see the old thread):

> .`discard` is a terrible default, especially for stderr, because it will cause many people (mostly but not exclusively beginners) to unwittingly miss that their subprocess error'd out.

I would agree with this if we had a "read all and never deadlock" or "read 64kb and never deadlock" option. That would be a perfect default value. But we don't. Btw. why not? As I explained in the long post this should be technically possible. Currently we only have: "read X, but sometimes deadlock when X + *platform_specific_value* do not match".

Whatever option we choose (as far as the default values go) can we at least make them the same? In the proposal we have (this is the variant with the `body` closure):

```swift
public static func run<R>(
  …
  output: RedirectedOutputMethod = .redirect,
  error: RedirectedOutputMethod = .discard,
  _ body: (@Sendable @escaping (Subprocess) async throws -> R)
) async throws -> Result<R>
```

I had a 100% deadlock scenario that I wanted to include in this post. The problem is that it did not deadlock. Hmm… It took me a few minutes to realize that the default for `output` is `redirect` and for `error` is `discard`. I forgot about this, I just copied the `standardOutput` code, changed to `standardError` and thought it would work. In other words: I used the discarding `standardError` thinking that it is `redirect`, because that was the default for `standardOutput`.

This makes it easy for users to miss `stderr`, because they forgot that the default is `discard`. No compiler error, no precondition, no exception, no assertion, it just returns `nil` that my autocomplete discarded with `p.standardError?.xxx`. It looked correct, but in fact it was a dead code, because the stream was redirected to `/dev/null` and not to my handler.

## `Collected` - reading deadlocks

This will be our child program, it will write 70*1000 bytes to `stderr`:

```swift
import SystemPackage

let buffer = [UInt8](repeating: 0, count: 1000)

for _ in 0..<70 {
  try FileDescriptor.standardError.writeAll(buffer)
}
```

Parent:

```swift
let result = try await Subprocess.run(
  executing: .at(FilePath(".build/debug/princess_is_in_another_stream"))
)
```

**Expected:** In the result variable:
- `stdout` is empty
- `stderr` has 70_000 bytes

**Result:** deadlock

We are doing a blocking read on `stdout`, while the child writes to `stderr`, fills the pipe and waits for somebody to read.

How probable is this? I don't know. Can we guarantee that no such program exist? No.

I kind of feel that the difference between `stdout` and `stderr` is blurry. [glibc says](https://www.gnu.org/software/libc/manual/html_node/Standard-Streams.html):
> Variable: FILE * stderr
>
> The standard error stream, which is used for error messages and diagnostics issued by the program.

For example Swift Package Manager writes this to *stderr*:

```
Fetching https://github.com/apple/swift-system from cache
Computing version for https://github.com/apple/swift-system
Fetched https://github.com/apple/swift-system (0.65s)
Computed https://github.com/apple/swift-system at 1.2.1 (0.29s)
Creating working copy for https://github.com/apple/swift-system
Working copy of https://github.com/apple/swift-system resolved at 1.2.1
```

For them this is a diagnostic, and programs are allowed to print as many of those as they want. Nothing wrong has happened, there is no error. But once they reach the pipe buffer size it will deadlock. And I will not blame the Swift Package Manager team for this.

Maybe we should read the `stdout/stderr` in parallel. Maybe we should do something else. But I do not feel like a deadlock is a valid thing to do. Again, notice that I am using the default values for all of the `Subprocess.run` arguments.

## `body` closure - SIGPIPE in child

```swift
let result = try await Subprocess.run(
  executing: .at(FilePath("\(bin)/cat")),
  arguments: ["Pride and Prejudice.txt"]
) { _ in
  return 1
}

print(result.terminationStatus)
```

**Expected:** prints "0"

**Result:** prints "unhandledException(13)" <-- `SIGPIPE`

In general this is will happen when `body` closure exits before the last `stdout` from the child. We are basically using `stdout/stderr` as a synchronization primitives.

I'm not really sure if by looking at the code I would expect crashing the child with `SIGPIPE`. This behavior may be valid, but neither the documentation nor the proposal mention it. I would call it *surprising*. And it leaves user with no information about the *why*. Where is the error? I could see somebody wasting many hours on this.

## `body` closure - `stdin` deadlock

```swift
let result = try await Subprocess.run(
  executing: .at(FilePath("program"))
) { p, writer in
  return 1
}
```

**Expected:** Did you notice the change from the program in the previous section? It is very subtle.

**Result:** Possible deadlock depending on what the `program` is.

The call to `try await writer.finish()` is missing. If `program` loops infinitely reading `stdin` and performing some actions, then it will never finish, because we forgot to close the `stdin`. And because, `writer.finish()` is `try await`, we can't put it in `defer`.

In the long post I mentioned that I do not see the reason for `finish/close` call to be mandatory. It should be optional. We could make the this method idempotent and make sure that the `Subprocess` will ALWAYS call it.

Scenario 1:
1. User calls `close` -> we close the file
2. `Subprocess` calls `close` -> nothing happens

Scenario 2:
1. User forgets to call `close`
2. `Subprocess` calls `close` -> we close the file

For example:

```swift
actor StandardInputWriterActor {
  private let fileDescriptor: FileDescriptor
  private var isClosed = false

  public func close() async throws {
    if !self.isClosed {
      self.isClosed = true
      try self.fileDescriptor.close()
    }
  }
}
```

Now we just need to find a good spot for the `Subprocess` to call it. We can call `close` as many times as we want, only the 1st one matters, this way we go from:

> User HAS to call `close` otherwise possible deadlock.

To:

> User MAY call `close`. Subprocess will call it ALWAYS. No deadlock.

In the old thread I had a talk about this with @wadetregaskis, and their final stance was:

> It's not about calling it multiple times, it's about ensuring it's called [at least] once.
>
> Some cases don't care if it's called - maybe the subprocess in question doesn't wait on stdin and will exit regardless. But it doesn't hurt to close stdin in that case, and it's safer to err that way.

`Subprocess` will call it! That's the whole point of making it idempotent. We can call it even if the user has already called it. But if they forgot, then there is always a safety-call done by the `Subprocess`.

## `body` closure - `stdout` deadlock

For this one let's ignore the `SIGPIPE`-ing the child for a second:

```swift
let result = try await Subprocess.run(
  executing: .at(FilePath("\(bin)/cat")),
  arguments: ["Pride and Prejudice.txt"],
  // I typed the explicit '.redirect', because the default values are
  // different for 'output' and 'error'. Just to avoid confusion.
  output: .redirect,
  error: .redirect
) { p in
  return 1
}
```

Deadlock. Oh… we need to read the pipes. This will also prevent `SIGPIPE`.

```swift
let result = try await Subprocess.run(
  executing: .at(FilePath("\(bin)/cat")),
  arguments: ["Pride and Prejudice.txt"],
  output: .redirect,
  error: .redirect
) { p in
  // There is no "read all and discard" or "forEach", I will just use 'reduce'.
  // '!' because YOLO. It's not like I can handle 'nil' meaningfully anyway.
  try await p.standardOutput!.reduce(()) { (_, _) in () }
  try await p.standardError!.reduce(()) { (_, _) in () }
  return 1
}
```

It will work… in this case. But at this point we all know that it is not correct. The `stderr` may fill and deadlock. I will use the same program as before to write 70*1000 bytes to `stderr`:

```swift
let result = try await Subprocess.run(
  executing: .at(FilePath(".build/debug/princess_is_in_another_stream")),
  output: .redirect,
  error: .redirect
) { /* Same as above. */ }
```

Deadlock. We need to read them in parallel!

```swift
let result = try await Subprocess.run(
  executing: .at(FilePath(".build/debug/princess_is_in_another_stream")),
  output: .redirect,
  error: .redirect
) { p in
  // 'withDiscardingTaskGroup' is only on macOS 14
  try await withThrowingTaskGroup(of: Void.self) { group in
    group.addTask { try await p.standardOutput!.reduce(()) { (_, _) in () } }
    group.addTask { try await p.standardError!.reduce(()) { (_, _) in () } }
    try await group.waitForAll()
  }

  return 1
}
```

It works! As far as I know this is deadlock proof.

Now, if we use the closure with `StandardInputWriter` then our total boilerplate is:

```swift
try await writer.finish()

try await withThrowingTaskGroup(of: Void.self) { group in
  group.addTask { try await p.standardOutput!.reduce(()) { (_, _) in () } }
  group.addTask { try await p.standardError!.reduce(()) { (_, _) in () } }
  try await group.waitForAll()
}
```

We have to do this every single time we use the `body` closure overload to avoid `SIGPIPE` or deadlock. Are we sure that our users will be able to write it? It looks quite complicated.

## SIGPIPE - parent

There is an obvious `SIGPIPE` on the parent, but we can't do anything about it. If we tried to convert it into `EBADF` that would be a race condition. I would take "always `SIGPIPE`" over "`EBADF` but once in a blue moon `SIGPIPE`".

That said, I see no reason why we allow sending signals after we confirmed the process termination. Pid reuse is a "theoretical" issue, but still an issue. (I mentioned this in my long post.)

## Multiple processes - deadlock/crash/custom scheduler?

This module does a lot of blocking on cooperative threads: `waitpid`, `read`, `write`. From what I see only `AsyncBytes.read` is done using `DispatchIO`. And there are many possible deadlocks. Personally I would try to move everything outside of the Swift Concurrency, but as long as it does not leak outside of the module it is fine. But it leaks.

In this section we will assume that deadlocks are not possible, and everything always works perfectly. This will start `sleep 5` 10 times:

```swift
let SLEEP_COUNT = 10
let start = DispatchTime.now()

try await withThrowingTaskGroup(of: Void.self) { group in
  for _ in 0..<SLEEP_COUNT {
    group.addTask {
      let result = try await Subprocess.run(
        executing: .at(FilePath("\(bin)/sleep")),
        arguments: ["5"]
      )

      print(result.terminationStatus)
    }
  }

  try await group.waitForAll()
}

let duration = DispatchTime.now().uptimeNanoseconds - start.uptimeNanoseconds
print("Total: \(duration / 1_000_000_000)s")
```

**Expected:** It finishes in ~5s.

**Result:** Possible deadlock/crash. Even if it didn't it would be more than 5s.

My original idea for this test was to show that running more than 2/4/8/… processes at the same time is not possible because of the blocking calls.

**Use case 1:** We have a program that subscribes to a Message Queue. After getting a message it starts a process depending on the message content. If we receive a lot of messages we may need to start multiple processes at the same time. This would not be possible with `Subprocess.run`. We end up with a back-pressure scenario. I think that OS scheduler would deal with it just fine, but this module overrides the OS scheduler.

**Use case 2:** Olympics are coming and I am interested in running, swimming and rhythmic gymnastic. Unfortunately during the competitions I am at work, so I decided to write an app that will scrape html page and download a video with `ffmpeg`. You can't do this with `Subprocess.run` because it may happen that when you are recording running and swimming it will not be able to start rhythmic gymnastic. We just lost user data.

That was the theory and my initial assumption about this test case. What **actually** happens depends on the `SLEEP_COUNT` value. If you go too far it will deadlock/crash. I tested this on Intel Pentium G4560 (Ubuntu 22.04.4 LTS) which has only 2 cores and `SLEEP_COUNT = 2` would crash.

You know how computer games have those minimum requirements? Like Cyberpunk 2077 requires Core i7-6700 etc. With this module our programs have minimum requirements.

Each process requires 2 parallel tasks. Maybe 3 for `waitpid` and 2 parallel reads from `stdout/stderr`. There is some math formula that would allow us to calculate minimum requirements of a given program, but it is not in the proposal. I think: `3 x number_of_processes` is safe.

Similar thing happens then you start piping data from one process to another. All of them have to be alive at the same time. I have no example because this requires indentation (nesting `Subprocess.run` within another `Subprocess.run` closure), and that makes it too complicated and visually noisy/distracting for this post.

Anyway, now you have this number that you have remember and if you (by mistake) deploy your program to the machine that does not satisfy the minimum requirements then it will deadlock.

Btw. We just deadlocked without filling the pipe buffer. There are some other pipe buffer related deadlocks that I do not show here, as at this point everyone knows the drill, so it would be repetitive. I wanted to show something different.

## Documentation

There is none?

## End

I'm going to stop here, as at this point both of my posts added together are longer than the proposal itself. Check out my [old post](https://forums.swift.org/t/pitch-swift-subprocess/69805/53), if you want more.

I see that the proposal authors are trying to push a lot of things as "user errors", but I'm not sure if I agree. I think we should try to tackle as many of those scenarios as possible, or at least give users some tools to handle them. `Subprocess.run` looks deceptively simple, but it has multiple corner cases. It is declarative-like, users jus say `git status limit 500`, and they do not care about the details. Neither should they! For example we could:

- do not deadlock after the `limit + platform_specific_value`
- close `stdin` if they forget
- do not `SIGPIPE` the child, or at least mention it in documentation
- do not require the users to write parallel read from `stdout/stderr`, give them a method to do it with 1 call

Also, I just can't fail to notice that the authors of the proposal fall for the same pitfalls that they expect the users to avoid. For example blocking read on `stdout` while ignoring `stderr`. Or finite pipe buffer size. Users do not even know what pipes are! They can't account for this. And, from what I see, deadlocks are never mentioned in either the proposal or the documentation.
