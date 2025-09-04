// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "aupresetgen",
    platforms: [
        .macOS(.v10_15)
    ],
    products: [
        .executable(name: "aupresetgen", targets: ["aupresetgen"])
    ],
    dependencies: [
        .package(url: "https://github.com/apple/swift-argument-parser.git", from: "1.2.0")
    ],
    targets: [
        .executableTarget(
            name: "aupresetgen",
            dependencies: [
                .product(name: "ArgumentParser", package: "swift-argument-parser")
            ]
        )
    ]
)
