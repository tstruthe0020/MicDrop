// swift-tools-version:5.7
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
        .package(url: "https://github.com/apple/swift-argument-parser", from: "1.0.0")
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