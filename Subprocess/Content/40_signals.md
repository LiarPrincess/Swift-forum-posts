## Signals - `ESRCH`

Should signals throw on `ESRCH`? In my implementation:

```swift
/// - Returns: `true` if the signal was delivered. `false` if the process
/// was already terminated.
@discardableResult
public func sendSignal(_ signal: Signal) throws -> Bool
```

Most of the time you send `SIGKILL/SIGTERM`. If the process is already terminated they do nothing. I'm not sure if this is an error that we need to `throw`. If you really need this information then you can check the `Bool` return.

Also, this is a race condition. You think that the process is running, you send `SIGTERM`, but in the meantime the process has terminated. Is this a reason `throw`?

## Signals - Duplicate `pid`

I'm not exactly sure if I'm correct, but I think that after the process has terminated its `pid` is available for reuse. Same thing as `FileDescriptors`, but IIRC files guarantee the lowest value from the table, and pids do not.

So in theory:
1. We start a process with closure `body` argument
2. Process terminates
3. `body` still runs
4. OS reuses pid
5. `body` sends `SIGTERM`

Is this possible? Idk.

In my implementation after the `waitpid` thread finishes I set the `actor Subprocess` state to `terminated(exitStatus: CInt)`. From now on all of the `sendSignal` calls will do nothing and return `false` (meaning that process was terminated).
