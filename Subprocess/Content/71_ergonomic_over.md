## Ergonomic & documentation - Overhaul

TLDR; Rename `Subprocess.Configuration` to `Subprocess` and move `run` methods there.

```swift
public struct Subprocess2 {

  public let executable: Executable
  public var arguments: Arguments
  public var environment: Environment
  public var workingDirectory: FilePath?
  public var platformOptions: PlatformOptions

  /// PATH lookup.
  public init(
    executableName: String,
    arguments: Arguments = Arguments(),
    environment: Environment = .inherit,
    workingDirectory: FilePath? = nil,
    platformOptions: PlatformOptions = .default
  )

  /// Absolute/relative path.
  public init(executablePath: FilePath, …)
}
```

In summary:
- we have an initializer - which is what users expect
- this step is pretty small - you mostly have to choose between `executableName` and `executablePath`
- documentation is pretty short (but obviously longer than here) - only the difference between `executableName` and `executablePath` is highlighted. Mention that the other arguments are just setters. There is no `input/output/CollectedResult` etc., which makes learning more "bite-sized".

Code completion is:

![init-code-completion](img_subprocess2_init.png)

For running we have the same 6 overloads:

```swift
public struct Subprocess2 {

  public func runCollectingOutput(
    input: InputMethod = .noInput,
    output: CollectedOutputMethod = .collect,
    error: CollectedOutputMethod = .collect
  ) async throws -> CollectedResult { … }

  // I renamed 'Subprocess' to 'RunningSubprocess' in 'body'.
  // The result is now 'InteractiveResult'.
  public func runInteractively<R>(
    input: InputMethod = .noInput,
    output: RedirectedOutputMethod = .redirect,
    error: RedirectedOutputMethod = .discard,
    _ body: (@Sendable @escaping (RunningSubprocess) async throws -> R)
  ) async throws -> InteractiveResult<R> { … }

  // +overloads for different 'input'
}
```

The user flow is:
1. They need to `run/start/fork` - they will probably look for a method. They may have seen it while setting the properties.
2. Now they have to choose between `runCollectingOutput` and `runInteractively`.

    ![a](img_subprocess2_run.png)

    Before they even open the documentation they can see that:
    - all methods have some `input` argument
    - `Collecting` methods have `CollectedOutputMethod`
    - `Interactive` methods have `body: (RunningSubprocess -> R)`

    I guess the closure with `RunningSubprocess` is the difference, and that's why it is "interactive". The documentation is also shorter and focuses on the difference between `CollectingOutput` and `Interactive` not on `Executable/Arguments/Environment`.

3. Then they choose one of the overloads - you can clearly see that the difference is the `input`: `InputMethod/Sequence/AsyncSequence`.

In theory you could call the `runCollectingOutput/runInteractively` multiple times. Idk. if this is a feature we want/need.
