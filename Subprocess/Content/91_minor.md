## `SystemPackage.Errno`

Swift system [has a really nice `Errno` type](https://github.com/apple/swift-system/blob/main/Sources/System/Errno.swift):

```swift
do {
  let byteCount = try fd.read(into: buffer)
} catch Errno.wouldBlock, Errno.resourceTemporarilyUnavailable {
}

// Or:

internal func system_kill(pid: pid_t, signal: CInt) -> Errno? {
  let result = kill(pid, signal)
  if result == -1 { return .current }
  return nil
}
```

They did a really good job, and I like it. I makes everything so much nicer to read/write. I also like their convention of `system_` prefix for syscalls.

## CustomStringConvertible

`"\(Pid): \(executable) \(args trimmed to 20 characters)"`

Or maybe the same as `ps a` -> `COMMAND` column.

## Process outliving its parent

@jaredh159 (Jared Henderson) wrote:
> Just wanted to quick chime in that the behavior of a spawned process outliving it's parent (and being reparented by the OS) is sometimes exactly what you want…

For my implementation I was thinking about adding `Bool` flag to disable termination tracking (`waitpid` thread). You can still do this: just start a process and never `wait` it. This ends parent and orphans the child.

I didn’t, because it is rather niche use case. Most of the time you want to spawn a daemon. This is platform specific. In practice I would just use one of the C templates that eventually calls Swift. So, at least for daemons, I think it is a non-issue. Do you have some other use case?

Not sure where the proposal stands on this. AFAIK old foundation can do this, but I have not tested it.

## Overall proposal evaluation

Needs work.
