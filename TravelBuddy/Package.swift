// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "TravelBuddyKit",
    platforms: [.macOS(.v14)],
    products: [
        .library(name: "TravelBuddyKit", targets: ["TravelBuddyKit"]),
    ],
    targets: [
        .target(
            name: "TravelBuddyKit",
            path: "TravelBuddy",
            exclude: [
                "Info.plist",
                "Resources",
                "TravelBuddyApp.swift",
            ]
        ),
        .testTarget(
            name: "TravelBuddyKitTests",
            dependencies: ["TravelBuddyKit"],
            path: "Tests/TravelBuddyKitTests"
        ),
    ]
)
