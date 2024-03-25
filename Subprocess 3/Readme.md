## Deadlocks

I do not like deadlocks. Exceptions get a lot of flack for being hard to use, but they are nothing when compared with deadlocks. Obviously, it is not about replacing deadlocks with exceptions (not possible anyway). I just can't imagine dealing with deadlocks in production, it just **can't happen**. (I will assume that deadlocks that block Swift concurrency threads forever are just a bug in the proof of concept.)

There is an inherent deadlock within the domain: fill pipe and `waitpid` (there are a few others, but I think that this is the most common user-induced one). The proposal takes this single deadlock and splits it into 5 different scenarios where each one deadlocks. This is very difficult for the users, as knowledge from 'collecting' runs does not transfer to 'interactive' (the one with `body` closure).

I would go as far as saying: any design that does the split (like separate `Subprocess.run` for collection/interaction) multiplies the amount of possible deadlock scenarios that users have to remember. Especially if those scenarios have sub-scenarios with deadlocks (which they do). This is how we arrive at 5 deadlocks instead of 1, and at this point I just can't believe that we can call them "user errors".


## NSProcess piping deadlocks

[quote="wadetregaskis, post:108, topic:70337"]
`NSProcess` doesn't suffer from this because it doesn't block awaiting subprocess exit unless you explicitly tell it to (e.g. with [`waitUntilExit`](https://developer.apple.com/documentation/foundation/process/1415808-waituntilexit)).
[/quote]

[quote="icharleshu, post:110, topic:70337"]
I understand the difference here is that `NSTask` allows you to explicitly wait for child processes (which makes deadlocking less likely) while `Subprocess` doesn't, but as you pointed out it's possible do with `async let`.
[/quote]

The `NSProcess` makes deadlocks almost impossible:

```swift
let p1 = Process(stdout: pipe.writeEnd)
p1.waitUntilExit() // <-- this
let p2 = Process(stdin: pipe.readEnd)
p2.waitUntilExit()
```

People understand that piping data from `p1` to `p2` requires both of them to be alive at the same time, so they will move the `p1.waitUntilExit()` after the `p2` started. They will write the correct code "by default", because the code above explicitly says: I want the `p1` to finish before `p2`.

[quote="icharleshu, post:101, topic:70337"]
You can achieve this today by manually using a pipe:

```swift
let (readFd, writeFd) = try FileDescriptor.pipe()
let ls = try await Subprocess.run(
    executing: .named("ls"), output: .writeTo(writeFd, closeWhenDone: true), error: .discard)
let grep = try await Subprocess.run(executing: .named("grep"), arguments: ["test"], input: .readFrom(readFd, closeWhenDone: true))
let output = String(data: grep.standardOutput!, encoding: .utf8)
```
[/quote]

Code like this should **never** be written. This is "the default way", and people will assume that it works. In reality we **always** have to run them in parallel. Even if the deadlock does not seem to be possible *right now*, it may happen in the future when `ls` writes enough to deadlock. This is a "gotcha"  that our users have to realize. Writing parallel is not easy as we have to do `async let`/task group/nested, and that's a lot of code for something that is a relatively common use case. And, this is not the "default" code.

Side-note: I think that in practice a lot of the people will just skip the pipe and do the `child_1 -> parent -> child_2`, because `stdout -> stdin` compose (which they shouldn't):

```swift
let ls = try await Subprocess.run(…, output: .redirect)
let grep = try await Subprocess.run(…, input: ls.standardOutput!)
```

Can't imagine a situation where this is what we want. If we truly want the `parent` in the middle (for processing/inspection) then we should pipe to parent explicitly.

## Future piping

[quote="icharleshu, post:101, topic:70337"]
```
let chained = Subprocess.Configuration().then(Subprocess.Configuration())
let results = chained.run()
for try await result in results { ... }
```
[/quote]

It may be a bit complicated:
- `Chain` needs to be *chainable* to another chain/subprocess: `cat | grep | ws`, becomes `(cat | grep) | ws`. At some point it becomes "syntax heavy" where the amount of code occludes the intention.
- interactive run (the one with the `body` closure) may not be possible, especially if it occurs in the middle of the pipeline (use case: avoiding buffering tha data in parent).
- `Subprocess.Configuration` does not have a `stdin` parameter, this may be problematic if we want to provide input to the 1st process.
- pipes connect `stdout -> stdin` (which covers 95% of use cases), but as soon as we need some special configuration (write `stderr` to file; `stderr -> stdin`; etc.) we have to write something custom. This is a bit inflexible given the amount of work it requires.

Btw. this will be the 3rd API to run subprocess:
1. `Subprocess.run` that collects output
2. `Subprocess.run` with `body` closure
3. piping with `then`

Isn't that too much? All of them have different deadlocks/pitfalls. We end up with the "How not to deadlock" flowchart. Instead of 5 deadlock scenarios that we currently have we will have 7.


## Other languages

Just a quick review:

- blocking Python - `cat | grep | wc`:

  ```py
  from subprocess import *

  # Starts the child process. It DOES NOT block waiting for it to finish.
  cat = Popen(["cat", "Pride and Prejudice.txt"], stdout=PIPE)
  grep = Popen(["grep", "-o", "Elizabeth"], stdin=cat.stdout, stdout=PIPE)
  wc = Popen(["wc", "-l"], stdin=grep.stdout, stdout=PIPE)

  stdout, _ = wc.communicate() # wait for 'wc' to finish
  print(str(stdout, "utf-8"))  # prints 645
  ```

  In summary:

  - all processes run in parallel by default
  - `wc.communicate()` prevents "filled pipe" deadlocks
  - `waitpid` happens in the background - no zombies
  - sub-optimal piping with parent in the middle

- async Python - I have never used it, but the API [looks identical](https://docs.python.org/3/library/asyncio-subprocess.html) to blocking Python.

- Java has [`ProcessBuilder`](https://docs.oracle.com/javase/8/docs/api/java/lang/ProcessBuilder.html) for creating the process, probably because they do not have enums with payload. Then they have the [`Process`](https://docs.oracle.com/javase/8/docs/api/java/lang/Process.html) which is similar to Python `Popen`. They warn about the deadlock in the 3rd paragraph (the long one).

  ```java
  ProcessBuilder builder = new ProcessBuilder("notepad.exe");
  Process process = builder.start();
  assertThat(process.waitFor() >= 0);
  ```

- C# also has [Process class](https://learn.microsoft.com/en-us/dotnet/api/system.diagnostics.process?view=net-8.0):
  ```c#
  using (Process myProcess = new Process()) // IDisposable
  {
      myProcess.StartInfo.FileName = "C:\\notepad.exe";
      myProcess.Start();
      myProcess.WaitForExit()
  }
  ```

In conclusion: all of the programming languages adopt a similar model: create a  `Process` object and interact with it. We can still deadlock (example for Python):

```py
from subprocess import *

cat = Popen(["cat", "Pride and Prejudice.txt"], stdout=PIPE)
cat.wait() # call 'communicate()' to solve deadlock
```

But, documentation warns us about this in 3 different places (one of them is in a red box). And the fix is easy: replace `wait` with `communicate`.

I'm not saying that this is the only/best design possible, but nobody can argue that this approach makes piping safer and easier.



## Swift async/await

If we translated the `cat | grep | wc` from Python into Swift with `async/await`:

```swift
let catToGrep = try FileDescriptor.pipe()
let grepToWc = try FileDescriptor.pipe()

// Starts the child process. It DOES NOT block waiting for it to finish.
_ = try Subprocess(
  executablePath: "\(bin)/cat",
  arguments: ["Pride and Prejudice.txt"],
  stdout: .writeToFile(catToGrep.writeEnd) // close by default
)

_ = try Subprocess(
  executablePath: "\(bin)/grep",
  arguments: ["-o", "Elizabeth"],
  stdin: .readFromFile(catToGrep.readEnd),
  stdout: .writeToFile(grepToWc.writeEnd)
)

let wc = try Subprocess(
  executablePath: "\(bin)/wc",
  arguments: ["-l"],
  stdin: .readFromFile(grepToWc.readEnd),
  stdout: .pipeToParent // <-- this allows us to read the output in parent
)

let result = try await wc.readOutputAndWaitForTermination() // 'communicate' in Python
print(String(data: result.stdout, encoding: .utf8) ?? "<decoding error>") // 645
print(result.exitStatus) // 0
```

You can run this code using [this repository](https://github.com/LiarPrincess/Vampires-and-sunglasses) (this example is [already there](https://github.com/LiarPrincess/Vampires-and-sunglasses/blob/main/Sources/App/main.swift#L268)). It works exactly as Python:

- all processes run in parallel by default
- `wc.readOutputAndWaitForTermination()` is used for synchronization - it ensures that the process has terminated before we move on. It also prevents deadlocks due to the `readOutput` part. It DOES NOT block on the cooperative thread - it is just a `continuation` that is resumed when process terminates.
- all files are closed even if users forget
- `waitpid` happens in the background - no zombies. Process will be reaped (and its files closed) even if user never `waits` for it.
- piping is correct: `child_1 -> child_2` without the intermediate `parent`
- `_ = try Subprocess(…)` looks weird, but we are only interested in side-effects
- no custom scheduling - start as many processes as OS allows us. This is so crucial that I just have to assume that this is a bug in the proposal proof of concept.
- no deadlocks

It is definitely not as pretty as @davedelong solution with pipes: `let result = try await (list | grep | trim).launch()`. But I think it is a bit more flexible while still being user friendly: `.readFromFile` uses `pipe.readEnd`, and `.writeToFile` uses `pipe.writeEnd`, so it should be difficult to make a mistake. I see that the proposal avoids the word "pipe" (they use `.redirect` instead) this can confuse users when they get `EPIPE/SIGPIPE`.

Everything works as in the interactive (the one with `body` closure) mode in the proposal. If we want to collect output (similar to `Subprocess.run` that returns `CollectedResult`):

```swift
let result = try await Subprocess(
  executablePath: …,
  arguments: …,
  stdout: .pipeToParent,
  stderr: .pipeToParent
).readOutputAndWaitForTermination( /* onTaskCancellation: */ )
```

Same API for everything. Collecting is just a matter of calling `process.readOutputAndWaitForTermination()`. Piping is just `stdin: .readFromFile(pipe.readEnd)`, no special `.then`. And most importantly: no deadlocks in simple scenarios.

## Fin

I'm just not sure if any `Subprocess.run` benefits justify aiming deadlocks (plural for a good reason) at our feet. Tbh. the proposal has not convinced me that `Subprocess.run` has any **significant** advantage above the `NSProcess`/Python/Java/C#/C model. You do not get the `Task == Process` semantic, but it also means that you do not have to deal with parallel `Tasks`.
