## IO - File ownership for `close`

@beaumont wrote:

> Because .readFrom(_:) and .writeTo(_:) both take FileDescriptor I tab-completed my way into a footgun, by passing .standardInput, .standardOutput, and .standardOutput to input, output, and error respectively. This of course was silly for me to do, because they got closed after the process exited.

I was thinking about the same thing! But it may be a little bit more complicated:
- single `shouldCloseFiles` switch - as soon as you set it to `false` you have to close ALL of the files by yourself. Obviously, it is really easy to forget to do so.
- separate `shouldClose` per file - you have to remember which files you have to close, and closing them twice may be an error. So does forgetting it. I went this way in my implementation.

The real semantic that we are trying to express is: `move = close`, `borrow = do nothing`. If we ignore all of the `enums` and the overload explosion we would have:

```swift
func run(…, stdout: borrowing File, …) async throws -> CollectedResult
func run(…, closingStdout: consuming File, …) async throws -> CollectedResult
```

The `consuming` version would call the `borrowing` one and then close the file. Obviously `deinit` would not call `close`. It is the other way around: `consuming func close()` will end lifetime and `deinit` does nothing .

If we go back to reality (column wise):

|InputMethod            |CollectedOutMethod |RedirectedOutputMethod|
|-----------------------|-------------------|----------------------|
|noInput                |discard            |discard               |
|readingFrom `borrowing`|writeTo `borrowing`|writeTo `borrowing`   |
|readingFrom `consuming`|writeTo `consuming`|writeTo `consuming`   |
|                       |collect            |redirect              |
|                       |collect(limit:)    |                      |

A lot of the overloads! And we can't use `enum` because we can't store `borrowing`. We can't use protocols, because move-only do not support them. But we can:

```swift
// For a second let's assume that FileDescriptor is move-only.

struct CollectedOutputMethod: ~Copyable {
  private enum Storage: ~Copyable, Sendable {
    case consuming(FileDescriptor)
    case borrowing(FileDescriptor)
  }

  static func writeAndClose(_ f: consuming FileDescriptor) -> CollectedOutputMethod {
    return CollectedOutputMethod(raw: .consuming(f))
  }

  static func write(_ f: borrowing FileDescriptor) -> CollectedOutputMethod {
    // We can't copy a FileDescriptor, but we can copy its properties.
    // It works as long as we do not try to close it.
    let copy = FileDescriptor(<copy properties>)
    return CollectedOutputMethod(raw: .borrowing(copy))
  }
}
```

Some people may not like it because we are (de-facto) copying the move-only object. I think it is all about the semantic of move-only, not about *being* move-only. And the semantic is: call `close` to `consume`. In the `borrowing` branch we will never call `close`. It is kind of like in move-only smart pointers we can copy the pointer, but the contract says that we should also increment `refCount`. Copy is allowed it is all about the semantic.

Obviously this is not possible because `FileDescriptor` is not move-only as we have to be compatible with the old Foundation. This was a theoretical exercise, but maybe somebody has some solution.


## IO - Closing error

I already mentioned it a few weeks ago, but to have everything in 1 place:

Currently even if the process terminated successfully (regardless of the status), but the closing threw an exception then:
- the parent process (aka. our code) will only get the file closing exception - even if the state of the world (for example database) has changed.
- other files will not be closed.

There is a possible double closing issue.
