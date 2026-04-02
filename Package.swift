// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "VibereaderMenuBar",
    platforms: [.macOS(.v13)],
    products: [
        .executable(name: "VibereaderMenuBar", targets: ["VibereaderMenuBar"])
    ],
    targets: [
        .executableTarget(
            name: "VibereaderMenuBar",
            path: "Sources/VibereaderMenuBar",
            exclude: ["Info.plist"]
        )
    ]
)
