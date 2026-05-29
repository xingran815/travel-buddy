import SwiftUI

struct LoadingView: View {
    var message: String = "Loading…"

    var body: some View {
        VStack(spacing: 12) {
            ProgressView()
                .controlSize(.large)
            Text(message)
                .foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }
}

struct ErrorBannerView: View {
    let message: String
    var retry: (() -> Void)? = nil

    var body: some View {
        VStack(spacing: 8) {
            Label(message, systemImage: "exclamationmark.triangle.fill")
                .foregroundStyle(.red)
                .multilineTextAlignment(.center)
            if let retry {
                Button("Retry", action: retry)
                    .buttonStyle(.bordered)
            }
        }
        .padding()
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }
}
