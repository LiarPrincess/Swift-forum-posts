## waitpid

The proposal does not exactly specify how `waitpid` happens, so the only thing that I have is the proof of concept:

```swift
extension Subprocess.Configuration {
  public func run<R>(…) async throws -> Result<R> {
    // (…)
    return try await withThrowingTaskGroup(of: RunState<R>.self) { group in
      @Sendable func cleanup() throws { /* Close files */ }

      group.addTask { waitpid(pid.value, &status, 0) }
      group.addTask {
        // Call the closure provided by the user. I removed uninteresting stuff.
        try await body()
        try cleanup()
      }

      while let state = try await group.next() {
        // Get the 'result' and 'terminationStatus'
      }
    }
  }
}
```

We have a blocking `waitpid` call on the cooperative thread. Tbh. even from the proof of concept I expected at least `waitpid(WNOHANG) + Task.sleep()` in a loop. I tried to start a few `ffmpeg` processes, and it didn't work.

Can the proposal at least mention that this is not how it will work in the real implementation?

I outlined a few solutions [here](https://github.com/LiarPrincess/Vampires-and-sunglasses/blob/main/Sources/Lib/Linux.swift#L262) with a link to CPython implementation.

## IO - Chatty children

Imagine this scenario:
1. Child process starts with `stdout` set to pipe
2. Child writes to `stdout`
3. Child writes some more…
4. Deadlock

How? Pipes are backed by a buffer, if nobody reads the buffer then `write` will wait until somebody does. This will deadlock with the `waitpid` and no reader.

The proposal does not mention this situation.

Though if we take the code from the proof of concept at the face value then as soon as the `body` finishes we will `close` the reading end of the pipe. This will `SIGPIPE` or `EPIPE` in the child. Well… you can't deadlock if you crash it first. Is that intended?

A more "human" approach would be to read all of the *nonsense* that the child writes and then `waitpid`. Or do it in parallel: 1 `Task` reads and the 2nd waits.

Python documentation explicitly warns about this situation for [`wait`](https://docs.python.org/3/library/asyncio-subprocess.html#asyncio.subprocess.Process.wait), that's why they recommend [`communicate`](https://docs.python.org/3/library/asyncio-subprocess.html#asyncio.subprocess.Process.communicate) for pipes.

Examples using the code from my repository (you can easily translate it to Python with `Popen`):

- 🔴 deadlock - pipe is full and the child is blocked
  ```swift
  let process = try Subprocess(
    executablePath: "/usr/bin/cat",
    arguments: ["Pride and Prejudice.txt"],
    stdout: .pipe,
  )

  let status = try await process.wait() // Deadlock
  ```

- 🟢 works - we read the whole `stdout` before waiting
  ```swift
  let process = try Subprocess( /* cat "Pride and Prejudice.txt" */ )
  let s = try await process.stdout.readAll(encoding: .utf8)
  let status = try await process.wait()
  ```

- 🟢 works - it reads `stdout/stderr` in parallel, so we do not deadlock on any of them
  ```swift
  let process = try Subprocess( /* cat "Pride and Prejudice.txt" */ )
  let status = try await process.readAllFromPipesAndWait() // 'communicate' in Python
  ```

## IO - Pipe buffer size

On Linux you can use `fcntl` with following arguments:
- `F_GETPIPE_SZ` - get pipe buffer size
- `F_SETPIPE_SZ` - set pipe buffer size; conditions apply

It may not be portable.

On my machine (Ubuntu 22.04.4 LTS) the default is `65536`. This is a lot, but still not enough to store the whole "Pride and Prejudice". You can just `cat` the whole thing for testing.

In theory we could allow users to specify the size of the buffer. I do not know the use case for this, and I'm not sure if anybody will ever complain if we don't. Long time ago I discovered that the more advanced features you use, the more things break. Anyway, if we want this then remember to ignore `EBUSY`.

I played with pipes [here](https://github.com/LiarPrincess/Vampires-and-sunglasses/blob/main/Sources/App/Tests/pipes.swift) to discover how they work, so you may want to check this out. Linux only.

## IO - Blocking

In "IO - Chatty children" I promised that it will not deadlock. I lied.

Tbh. I do not understand everything in `AsyncBytes`, but:

```swift
buffer.readFunction = { (buf) in
  // …
  let bufPtr = UnsafeMutableRawBufferPointer(start: buf.nextPointer, count: capacity)
  let readSize: Int = try await IOActor().read(from: file, into: bufPtr)
}

final actor IOActor {
  func read(from fd: Int32, into buffer: UnsafeMutableRawBufferPointer) async throws -> Int {
    while true {
      let amount = Darwin.read(fd, buffer.baseAddress, buffer.count)
      // …
    }
  }

  func read(from fileDescriptor: FileDescriptor, into buffer: UnsafeMutableRawBufferPointer) async throws -> Int {
    // this is not incredibly effecient but it is the best we have
    let readLength = try fileDescriptor.read(into: buffer)
    return readLength
  }
}
```

I'm not exactly sure what `try await IOActor().read(from: file, into: bufPtr)` does. It does not matter, I will just skip it.

Anyway, we have `fileDescriptor.read` and `Darwin.read` on cooperative threads. This method blocks. So currently we have:
- Task1 does `waitpid`
- Task2 waits for `read`

But when we `read` something it will unblock. Surely it will not deadlock. Right?

Right? 😭…

Right? 😭… 😭…

…

- Task1 does `waitpid`
- Task2 waits for `read`
- Process writes to `stderr`, fills the buffer and waits for somebody to read it

We are down 2 cooperative threads and we have a deadlock with the child process. *Ouch…*

Is there some prevention method for this? The proposal does not mention it. In the code we have "this is not incredibly effecient but it is the best we have" comment, but I do not know what it means.

A lot of people say that you should not block on the cooperative thread. I don't agree. I think you are *perfectly* fine with blocking (within reason…), and I would take it any day over *over-engineered* solution that does not work.

That said if we really wanted to *over-engineer* this:

- **Option A: Threads** - spin a thread for every `read`, then resume the `Continuation`. On cancellation (which we have to support!) just kill the thread.

  This is actually [how `waitpid` works](https://github.com/LiarPrincess/Vampires-and-sunglasses/blob/main/Sources/Lib/Linux.swift#L262) in my library. You start a process, I create a `waitpid` thread. Once the child terminates it [sends the message to `Subprocess` actor](https://github.com/LiarPrincess/Vampires-and-sunglasses/blob/main/Sources/Lib/Subprocess.swift#L317) which closes the files and resumes `wait` continuations (btw. they support cancellation, this is not as trivial as one may think).

  Threads are expensive, but in theory you can just have 1 thread for all IO and just `poll` the files. You can even monitor termination with Linux pid file descriptors, which gives us 1 thread for all of the `Subprocess` needs.

- **Option B: Non blocking IO** - this is what I do for IO. For files you open them with `O_NONBLOCK`, for pipes you set it later (btw. there is race condition in there).

  Reads from an empty pipe return `EWOULDBLOCK/EAGAIN`. In my implementation I just return `nil` as `readByteCount`, so that the user knows that nothing happened.

  If they really need to `read` something then they can use poor-person synchronization and do `Task.sleep`. Tbh. this is [exactly what I do](https://github.com/LiarPrincess/Vampires-and-sunglasses/blob/main/Sources/Lib/Subprocess%2BIO.swift#L207) when user calls `readAll`. Is this the best thing ever? Not. But it does not block. It is cooperative. And it supports cancellation.

  Blocking writes also return `EWOULDBLOCK/EAGAIN`, but it is a little bit more trickier, so read the POSIX docs. Writes `n > PIPE_BUF` may drop user data. This is what the spec says, but it also list the solution:
  - we can implement it on our side, but this is OS specific; on Linux you just split in `PIPE_BUF` chunks
  - or just go with Jaws/TopGear logic and let the users create a bigger pipe
  - or just mention `O_NONBLOCK` in documentation, and let the users deal with it

At this point we arrive to (unsurprising) conclusion: `Subprocess` should be 100% Swift concurrency neutral: it does not block and it respects cancellation. The library that I wrote archives this in following ways:
- `waitpid` is done in a separate thread:
  - when the process finishes naturally -> OS notifies the `waitpid` thread
  - `SIGKILL` -> our code sends signal -> child terminates -> OS notifies the `waitpid` thread
- all IO is done with `O_NONBLOCK`

## IO - `posix_spawn_file_actions_adddup2`

With this everything should… Not yet! We have an infinite loop!

```swift
public struct CollectedOutputMethod: Sendable, Hashable {
  // Collect the output as Data with the default 16kb limit
  public static var collect: Self
  // Collect the output as Data with modified limit
  public static func collect(limit limit: Int) -> Self
}
```

Why do I have to provide a limit (implicit 16kb or explicit)? I just want all! Is `Int.max` good for this? How about `Int.min`? `-1`? Tough luck: all of the will crash with SIGILL: illegal instruction operand.

Btw. what it the unit for `limit`? The proposal says: "By default, this limit is 16kb (when specifying `.collect`).". But in code we have `return .init(method: .collected(128 * 1024))`. Instead it should be `limitInBytes` or `byteCount`.

Anyway, you are miss-using the api. This works:

```swift
let (readEnd, writeEnd) = try FileDescriptor.pipe()
let buffer = UnsafeMutableRawBufferPointer.allocate(byteCount: 10, alignment: 1)
try writeEnd.close()

// When 'read' returns 0 it means end of the file.
while try readEnd.read(into: buffer) != 0 {
  // Code here never executes!
}
```

This is an infinite loop:

```swift
let (readEnd, writeEnd) = try FileDescriptor.pipe()
let buffer = UnsafeMutableRawBufferPointer.allocate(byteCount: 10, alignment: 1)
let writeEnd2 = dup(writeEnd.rawValue) // <-- I added this
try writeEnd.close()

while try readEnd.read(into: buffer) != 0 {
  // Infinite loop.
}
```

You are doing the 2nd one. With `posix_spawn_file_actions_adddup2` you send the file to the child, but you also have it in the parent process. The rule is: as long as there is `writeEnd` open then the `read` will never return `0`.

This combined with blocking reads means that our cooperative thread is down. But surely when the process exists it will unlock the thread? No. The `writeEnd` is closed after the `body` ends and we are inside the `body`. This is why everything should be `async`: still an infinite loop, but at least it is cooperative.

Anyway, you are supposed to close the child ends in the parent process. This is how in my implementation I can:

```swift
let s2 = try await Subprocess( /* cat "Pride and Prejudice.txt" */ ).stdout.readAll(encoding: .utf8)
```

It will read all, without any limits. We could allow users specify some limit, but it should be an option, not a mandatory api limitation.
