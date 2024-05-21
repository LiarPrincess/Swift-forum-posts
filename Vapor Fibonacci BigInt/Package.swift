// swift-tools-version: 5.10
// The swift-tools-version declares the minimum version of Swift required to build this package.

import PackageDescription

let package = Package(
  name: "Test",
  products: [
    .executable(name: "Main", targets: ["Main"]),
  ],
  targets: [
    .executableTarget(
      name: "Main",
      dependencies: ["Violet", "Attaswift", "Numberick"]
    ),
    .target(name: "Violet"),
    .target(name: "Attaswift"),
    .target(name: "NBKCoreKit", path: "Sources/NumberickCore"),
    .target(name: "Numberick", dependencies: ["NBKCoreKit"]),
  ]
)
