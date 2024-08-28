# Older thread

[quote="aetherealtech, post:5, topic:73969"]
A system of concurrency guaranteeing order is a contradiction. Concurrent *means* in parallel, which implies no guarantee of order. Guaranteeing order just reintroduces seriality.
[/quote]

[Concurrency is not Parallelism by Rob Pike](https://www.youtube.com/watch?v=oV9rvDllKEg) is a nice talk about this topic.

Concurrent does not mean parallel. It does not even imply parallel. Those are unrelated concepts. I would say the "concurrent" gives you the possibility of being parallel, but it does not mean that this would actually be the case.


[quote="aetherealtech, post:5, topic:73969"]
Regarding re-entrance, why does anyone want or expect actors to continue blocking all message processing after a process yields?
[/quote]

[quote="aetherealtech, post:5, topic:73969"]
It's not "this is the right place to put an `await`, it's "I put an `await` here because I have to". They want and need the whole function to be a single critical section but it just can't be because they happen to need to call an `async` function somewhere inside of it.
[/quote]

[quote="aetherealtech, post:5, topic:73969"]
This is also why people repeatedly ask "can't we just get rid of the `await` keyword?" They think it's for the compiler, but it's not. It's for *you*.
[/quote]

[quote="aetherealtech, post:5, topic:73969"]
This is the language forcing you to abandon poor design. It is equivalent to nested critical sections. (…) Nesting them violates this rule. Cooperative multitasking simply doesn't let you do this.
[/quote]

When you are using a lock in Swift you have and indentation:

```swift
self.lock.withLock {
  self.count += 1
}
```

Actors do not have indentation which makes is very difficult to remember that this is an *isolated* critical section between 2 `async` calls. Given how much of the surrounding "noise" there is in every method those 2 tiny `async` keywords just blend with the rest of the code.

Obviously blocking the actor for the whole duration of the method execution would deadlock. People know this, they are 100% aware of this fact. I have written my fair share of Swift concurrency code, but there is not even a single project where I would be confident that there are no re-entrancy related problems.

[quote="maartene, post:14, topic:73969"]
it is very hard - perhaps impossible - to write tests that give absolute confidence that actor re-entrance doesn't cause unexpected results
[/quote]

Yep. For this you would need an meta-scheduler that would look at all of the jobs scheduled a given time, run independent executions with all of the orderings, and fail if at least 1 execution failed. This is not possible as `Jobs` can schedule new `Jobs` and pretty soon we will have combinatorial explosion.

That said there are ways to manually control the execution order. I think the best thread would be [Reliably testing code that adopts Swift Concurrency? by @stephencelis](https://forums.swift.org/t/reliably-testing-code-that-adopts-swift-concurrency/57304). It was posted 2 years ago (may 2022), and not a lot has changed since then. From what I remember their conclusions were (btw. I do not follow their [pointfree.co](https://www.pointfree.co/) podcast, so maybe something has changed in the meantime):
- [MainSerialExecutor](https://github.com/pointfreeco/swift-concurrency-extras/blob/main/Sources/ConcurrencyExtras/MainSerialExecutor.swift)
- [Task.megaYield](https://github.com/pointfreeco/swift-concurrency-extras/blob/main/Sources/ConcurrencyExtras/Task.swift)

For me those 2 things are hacks. `Task.megaYield` does not guarantee `yield`, and `MainSerialExecutor` is just too complicated. Below I will share my own ways of dealing with those stuff.



# State machines

State machines work great and are a natural fit for concurrency.

Basically, with actor re-entrance we have a fully distributed system. There is no global state, we only see our local limited scope. It may happen that 2 outside entities independently request te same action:
1. Incoming request to perform operation "A"
2. Operation "A" awaits for some other operation
3. Another incoming request to perform operation "A"

An example would be: every cache that ever existed. You probably have seen a Swift implementation already. 1st result in duckduckgo is [donnywals.com/Using Swift’s async/await to build an image loader](https://www.donnywals.com/using-swifts-async-await-to-build-an-image-loader/) (non-affiliated).

Another example would be some kind of `finish/close` (pseudo-code, not tested):

```swift
actor Thingy {
  enum CloseState { open, inProgress(Task), closed }

  private var closeState = CloseState.open

  func close() async {
    switch self.closeState {
    case .open: …
    case .inProgress(let task): await task
    case .closed: break
    }
  }
}
```

The above code could also be rewritten with just `Task?`. It kind of suggests that the `Task` [is a state machine](https://github.com/swiftlang/swift/blob/main/stdlib/public/Concurrency/Task.cpp#L110).

[swift-async-algorithms](https://github.com/apple/swift-async-algorithms) also has some more examples: [ChannelStateMachine.swift](https://github.com/apple/swift-async-algorithms/blob/main/Sources/AsyncAlgorithms/Channels/ChannelStateMachine.swift) etc…

# Building blocks

Let's go back to the bad old days of just using threads. My way of approaching the situation was: "you are not clever enough, find already implemented data structure that does things for you".

For example I used an actor like pattern:
- each thread has a `ThreadProxy` class
- to run a method in the thread we call a method on the proxy
- to communicate between threads we use 2 `ConcurrentQueues`: inbox and outbox

With this our UI is always responsive, and if the user clicks very fast (faster than the background operations) we just buffer the actions in the `inbox: ConcurrentQueue`.

Anyway, going back to the Swift concurrency: what are the building block here?
- Task
- AsyncStream
- [swift-async-algorithms](https://github.com/apple/swift-async-algorithms)
- etc.

In a way we design our architecture based on those building blocks, instead of writing synchronous Swift, but with `actor` instead of `class`. For example instead of `actor` mutation we can send a message on a channel. This is easily testable because now we have an observable effect (the message). Representing behavior as data is a fairly interesting concept.

Below is an example of this, note that I do NOT propose this architecture to solve OP problem, it is just that some form of a "game" is a good way of illustrating things. I will use `AsyncPubSub` which facilitates fan-out many-to-many communication (we will look at the implementation later):
- messages can be send to the `AsyncPubSub`
- subscribers can subscribe to the `AsyncPubSub`
- each message is forwarded to all of the subscribers

(I feel like this data type should already be inside [swift-async-algorithms](https://github.com/apple/swift-async-algorithms), but for some reason it is not. I have already written the proposal a few months ago, I can post it if anybody is  interested.)

```swift
struct Move: Sendable { playerId: String, … }
struct GameState: Sendable { currentPlayerId: String, board: Board, … }

actor Player {
  private let id: String
  private let moves: AsyncStream<Move>.Continuation
  private let gameStates: AsyncPubSub<GameState>

  func run() {
    for await state in self.gameStates.subscribe() {
      guard state.currentPlayerId == self.id else { continue }
      let move = self.calculateMove(board: state.board)
      self.moves.yield(move)
    }
  }
}

actor GameLogic {
  private let moves: AsyncStream<Move>
  private let gameStates: AsyncPubSub<GameState>

  func run() {
    // Emit the initial state.
    self.gameStates.yield(self.state)

    for await move in self.moves {
      // You have to wait for your turn!
      guard move.playerId == self.currentPlayerId else { continue }
      // We can do an 'await' call.
      // If a player yields a move during the 'database.store' it will be added
      // to the 'AsyncStream<Move>' buffer. No re-entrancy.
      await self.database.store(move: move)
      self.updateState(move: move)
      // Notify everyone about the new state.
      self.gameStates.yield(self.state)

      if self.state.winner != nil {
        break
      }
    }

    // Cleanup, store game result in database etc…
    self.gameStates.finish()
  }
}

let (moves, movesContinuation) = AsyncStream<Move>.makeStream()
let states = AsyncPubSub<GameState>()

let playerA = Player(id: "A", moves: movesContinuation, states: states)
let playerB = Player(id: "B", moves: movesContinuation, states: states)
let logic = GameLogic(moves: moves, states: states)

withTaskGroup { group in
  // TODO: Subscribe to the 'states' in your UI.
  // TODO: For debug: 'print' every 'state' message.
  group.addTask { playerA.run() }
  group.addTask { playerB.run() }
  group.addTask { logic.run() }
}
```

This is a skeleton of what one can do. It is trivial to test. In reality there is a race condition where we may emit the initial state before our players subscribe, to solve it:
- instead of `AsyncStream<Move>` use `AsyncStream<PlayerAction>` where `PlayerAction = connect(playerId) | move(…)`
- in `GameLogic` use (you guessed it) state machine: `State = waitingForPlayers(connectedPlayerIds) | inGame(GameState)`. Wait for all of the players to `connect` before starting the game.

We may also want to add `PlayerAction.disconnect(playerId)` (forfeit?) for when the user just exists the game. This will immediately notify the other player that they won. With this the whole thing becomes a standard client-server application, we are just using typed `enums` instead of JSON over WebSocket.

Side-note: the whole design can be made sync via `protocol Player { func getMove(state:) -> Move }`, and the `GameLogic` would just call it. This is just an illustration of a pattern of using "building blocks", NOT A SOLUTION TO ANY PARTICULAR PROBLEM.

Happens before/after relationship between the messages may also be needed:
- player A makes a move
- game logic starts new state calculation
- player B makes a move
- game logic finishes state calculation after player A move
- I guess we already have a player B move, so we will use it <- this move was based on the old state (before the player A move) it may not be correct

To solve it we can just add `stateId` and then each move will include a `stateId` representing a state on which it was calculated. Game logic will reject all of the moves based on the old state. This gives us ordering of the messages.

Remember:
- all of the ids should be random guids - we don't want player A to guess player B id. (aimbot for chess?)
- get of the `actor` as soon as possible - if `calculateMove` is sync then it can be moved outside of the `actor` -> easier tests.


If we are implementing an AI bot (the "computer" player) then there is a fancy thing we can do: as soon as our bot emits a move it will try to predict the player move and pre-calculate its next move. This way when the player actually does the move we will already have calculated the response. This makes our bot very fast at the expense of the energy. We may want to disable this feature when the user is at less than 20% of the battery. Also, remember to use `background` priority for prediction. The design is concurrent, but we may not get a parallel execution.

Skeleton for prediction:

```swift
actor Player {
  private let id: String
  private let moves: AsyncStream<PlayerActions>.Continuation
  private let gameStates: AsyncPubSub<GameState>
  private var boardToPredictedMove = [Board:Move]()

  func run() {
    let subscription = self.gameStates.subscribe()
    // Notify 'GameLogic' that we are ready.
    self.moves.yield(.connected(playerId: self.id))

    for state in subscription {
      guard state.playerId == self.id else { continue }

      self.cancelUserMovePrediction()

      let move: Move

      if let predicted = self.boardToPredictedMove[state.board] {
        move = predicted
      } else {
        move = self.calculateMove(board: state.board)
      }

      self.boardToPredictedMove.removeAll()
      self.startPredictingUserMoves(state: boardAfterOurMove)
      self.moves.yield(move)
    }
  }
}
```

Anyway, this all goes back to the [Concurrency is not Parallelism by Rob Pike](https://www.youtube.com/watch?v=oV9rvDllKEg): you don't think about running things in parallel, you think about how to break the problem down into independent components that you can separate and get right, and then compose to solve the whole problem together. Basically: keep the gophers running, otherwise they are unemployed and their families starve.

As for the distributed systems: I don't remember the details (I read it 4 years ago) but "Designing Data-Intensive Applications" by Martin Kleppmann was a pretty good summary of how to design those. For example it talks about the importance of idempotence.

# Tests

[quote="ktoso, post:4, topic:73969"]
I tend to agree with the previous post, manually writing tests to prove you don't have some specific ordering somewhere that will cause a bug is a path that never ends and is unlikely to give you much real confidence... You could try hard and for every method consider every possible ordering things might arrive in it... but that's *a lot of thinking* and hardcoding orders as well.
[/quote]

Depends. From my experience a lot of code bases use a set of "core" data types. I think that it would be beneficial to test them thoroughly, because they are used in so many places. And for that we have to test different scenarios/orders to fully say: "this code works".

To illustrate the example let's quickly implement the `AsyncPubSub` that I mentioned before. The real implementation would probably be:
- store a \[de\]queue of `Messages`
- each `Message` holds:
  - `yieldCount: Int` - number of consumers at the time of 'yield/send'
  - `consumeCount: Int` - number of `next` calls that consumed this message
- when `consumeCount == yieldCount -> [de]queue.popMessage()`

This is a bit too complicated for this post, so we will just create a separate `AsyncStream` for each consumer.

```swift
final class AsyncPubSub<Message: Sendable>: Sendable {

  typealias SubscriptionId = UInt64

  final class Subscription: Sendable, AsyncSequence {
    let id: SubscriptionId
    let stream: AsyncStream<Message>
    let pubSub: AsyncPubSub<Message>

    func makeAsyncIterator() -> AsyncIterator { self.stream.makeAsyncIterator() }
    func finish() { self.pubSub.unsubscribe(self) }
    deinit { self.finish() }
  }

  private struct State {
    fileprivate var nextId = SubscriptionId.zero
    fileprivate var subscribers = [SubscriptionId:AsyncStream<Message>.Continuation]()
  }

  private let state = Locked(State())

  deinit { self.finish() }

  func send(_ event: Message) {
    self.state.lock { state in
      // If 'state.isFinished' -> dictionary is empty.
      for (_, continuation) in state.subscribers {
        continuation.yield(event)
      }
    }
  }

  func subscribe() -> Subscription {
    return self.state.lock { state in
      let id = state.nextId
      state.nextId += 1

      let (stream, continuation) = EventStream.makeStream() // unbounded
      let subscription = Subscription(…)

      if state.isFinished {
        continuation.finish()
      } else {
        state.subscribers[id] = continuation
      }

      return subscription
    }
  }

  func unsubscribe(_ subscription: Subscription) { … }
  func finish() { … }
}
```

We have following cases to tests:
- subscribe -> send message -> message is received
- send message -> subscribe -> nothing is received as we do not send past messages
- `AsyncPubSub.finish` -> subscribe -> empty
- `Subscription.finish` -> send message -> nothing is received

To test all of this we need some form of "order in the wild west of concurrency". For this I have my own `_test_event` library:
- `_test_event(object, message)` - emit an event
- `try await _test_event_wait(object, message, count: Int = 1)` - wait for an event to occur `count` times. `try` is for timeout.

A single test looks like this:

```swift
func test_subscribe_thenProduce_omNomNom() async throws {
  let bus = AsyncPubSub<Int>()

  // Subscribe -> collect
  try Task.withTimeout {
    let events = bus.subscribe()
    _test_event(bus, "SUBSCRIBE")
    let all = try await events.collect()
    XCTAssertEqual(all, [5, 42, -3])
    _test_event(bus, "DONE")
  }

  // Subscribe -> collect
  try Task.withTimeout {
    let events = bus.subscribe()
    _test_event(bus, "SUBSCRIBE")
    let all = try await events.collect()
    XCTAssertEqual(all, [5, 42, -3])
    _test_event(bus, "DONE")
  }

  // Wait for 2 subscriptions -> send messages
  try Task.withTimeout {
    try await _test_event_wait(bus, "SUBSCRIBE", count: 2)
    bus.send(5)
    bus.send(42)
    bus.send(-3)
    bus.finish()
  }

  try await _test_event_wait(bus, "DONE", count: 2)
}
```

Unfortunately not everything is as simple as the test above, so sometimes we have to emit a `test_event` in the production code. This is "ok", as there is a `#if DEBUG` check inside. It does not happen often.




# Isolate mutable state

Anyway, going back to the actor re-entrance: if the problem is only with state mutation in another `actor` then sort your properties by mutation corelation, as in "those 2 properties are always mutated together":

```swift
actor Thingy {
  let prop1: String
  let prop2: String

  var group1_bool: Bool
  var group1_array: [String]

  var group2_int: Int
}
```

`group1_bool` and `group1_array` are always mutated together, so let's move them to a separate type called `BoolArray`.

There is a certain movement in programming that adheres to "Make invalid states unrepresentable" mantra. The idea is that we model our data so that is is not possible to enter an invalid state -> the compiler catches the bugs for us.

Let's say that in our `BoolArray` example there is a state that will never occur (for example `(false, empty array)`), we model our newly created type to make it impossible to arrive there.

This way never forget to modify a property before doing an `await` call. This means that if we re-enter, our state is always valid. It is not pretty, but it scales nicely with the number of programmers in the project.

Obviously our newly created type (`BoolArray`) is an `actor`. Actually… not really. We can make it `Sendable` with `Lock/Mutex`.

```swift
final class SessionRegistry: Sendable, Sequence {

  private let idToSession = Locked([Session.Id:Session]())

  func get(id: Session.Id) -> Session? {
    self.idToSession.lock { $0[id] }
  }
}
```

(I will ignore the performance benefits of not using actors, performance NEVER matters. 99% of optimizations are premature.)

Swift stdlib will get `Mutex` soon (it took 3 years for something that is basically a must-have), but there are tons of custom implementations available. You can grab [swift-concurrency-extras/LockIsolated](https://github.com/pointfreeco/swift-concurrency-extras/blob/main/Sources/ConcurrencyExtras/LockIsolated.swift) from [pointfree.co](https://www.pointfree.co/). (Btw. just a reminder: never ever hold a lock during an `async` call.)

Anyway, locks are pretty great with Swift concurrency. They are also cheap. In certain cases you will be able to replace `actor` with `final class` which removes all of those pesky `await` calls.

It may depend on the coding style, but somehow in my case `var` properties are extremely rare. Maybe it is because I write a lot of unit tests, and having a mutable state makes testing difficult. IDK. It happened multiple times that I had an `actor` with a bunch of `Sendable let` properties which can be converted to `final class` without any problems.

# Global actors

You do not have to `await` if you run on the same actor.

I have seen people using `@MyGlobalActor` on property/function basis. For me this is an anti-pattern. It may make sense when you are writing the code, but try going back to it after a few months. It is just sooo… difficult to reason about.

I do not use global actors a lot, but when I do I tend to assign the whole domain to a single actor, so that everything is synchronized. I also include the actor name in the class name.

Example:

```swift
@globalActor
actor DatabaseActor: GlobalActor {
  static let shared = DatabaseActor()
}

@DatabaseActor
class Database {}

@DatabaseActor
class DatabaseRead {}
```

# Data structures

There is a whole word of data structures designed for concurrent access. A truly massive amount of academic works.

That said, they are not available in Swift, and I would advise not implementing them by hand.
