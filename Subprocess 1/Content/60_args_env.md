## Arguments - `ExpressibleByStringLiteral`

Proposal v2 has:

> Ideally, the `Arguments` feature should automatically split a string, such as "-a -n 1024 -v 'abc'", into an array of arguments. This enhancement would enable `Arguments` to conform to `ExpressibleByStringLiteral`, (…).

The `split` may fail if the `String` is malformed, and from what I see [`init(stringLiteral:)`](https://developer.apple.com/documentation/swift/expressiblebystringliteral/init(stringliteral:)) does not allow failures.

## Arguments - QOL

Minor QOL stuff:
- `public init(_ array: [String], executablePathOverride: String)` - can `executablePathOverride` be made optional? In the most common usage this parameter will not be supplied. Is this the same as @beaumont asked?

- `Arguments(CommandLine.arguments.dropFirst())` - do we want this? Obviously user can `Array(…)`.

## Environment - `init`

I assume that there is no `public` initializer for `Environment()` because that would be ambiguous between:
- empty collection - Swift convention; for example `Array<Int>()` means empty.
- `inherit` - which is what users really mean.

Maybe `custom` could be renamed to `empty`, this word already exists in Swift: `Array.isEmpty`.

## Environment - `strlen` bug

Just in case it slips through a code review later: `Subprocess.Configuration` -> `spawn` -> `createEnvironmentAndLookUpPath` -> `createFullCString`:

```swift
let rawByteKey: UnsafeMutablePointer<CChar> = keyContainer.createRawBytes()
(…)
let totalLength = keyContainer.count + 1 + valueContainer.count + 1
```

For `String`:
- `createRawBytes` does `strdup(string)`
- `keyContainer.count` returns `string.count`

Try this:

```swift
let s = "Łoś" // Polish word for moose
print(s.count) // 3 - number of grapheme clusters
print(strlen(strdup(s)!)) // 5 - number of bytes
```

Fun fact: my real-world name contains "ł". If create a directory using it (which 99% of users do) and put as a value in env then `totalLength` is incorrect as it treats `1 Character = 1 byte` while "ł" is `2 bytes`.
