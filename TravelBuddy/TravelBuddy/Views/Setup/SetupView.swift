import SwiftUI

// MARK: - ViewModel

private enum SetupState {
    case checking
    case downloading
    case done
    case error(String)
}

@MainActor
private class SetupViewModel: ObservableObject {
    @Published var state: SetupState = .checking
    @Published var progress: Double = 0

    private var sseClient: SSEClient?
    var onComplete: (() -> Void)?

    func start() {
        checkStatus()
    }

    func retry() {
        sseClient?.cancel()
        sseClient = nil
        state = .checking
        progress = 0
        startDownload()
    }

    private func checkStatus() {
        guard let url = URL(string: "\(BackendManager.baseURL)/api/setup/whisper-status") else {
            startDownload(); return
        }
        Task {
            if let (data, _) = try? await URLSession.shared.data(from: url),
               let json = try? JSONDecoder().decode([String: Bool].self, from: data),
               json["ready"] == true {
                state = .done
                onComplete?()
            } else {
                startDownload()
            }
        }
    }

    private func startDownload() {
        guard let url = URL(string: "\(BackendManager.baseURL)/api/setup/whisper-download") else {
            state = .error("Invalid URL"); return
        }
        state = .downloading
        var req = URLRequest(url: url)
        req.setValue("text/event-stream", forHTTPHeaderField: "Accept")

        let client = SSEClient()
        sseClient = client
        client.onEvent = { [weak self] payload in self?.handleEvent(payload) }
        client.onError = { [weak self] err in self?.state = .error(err.localizedDescription) }
        client.start(request: req)
    }

    private func handleEvent(_ payload: String) {
        guard let data = payload.data(using: .utf8),
              let json = try? JSONDecoder().decode(SetupEvent.self, from: data) else { return }
        progress = json.progress
        switch json.step {
        case "downloading": state = .downloading
        case "done":
            state = .done
            onComplete?()
        case "error":
            state = .error(json.message ?? "Download failed")
        default: break
        }
    }
}

private struct SetupEvent: Decodable {
    let step: String
    let progress: Double
    let message: String?
}

// MARK: - View

struct SetupView: View {
    var onComplete: () -> Void

    @StateObject private var vm = SetupViewModel()

    var body: some View {
        VStack(spacing: 24) {
            Image(systemName: "waveform.circle.fill")
                .font(.system(size: 72))
                .foregroundStyle(.blue)

            Text("Setting Up TravelBuddy")
                .font(.largeTitle.bold())

            Text("Downloading the Whisper speech recognition model (small, ~244 MB).\nThis happens once and enables offline transcription.")
                .multilineTextAlignment(.center)
                .foregroundStyle(.secondary)
                .frame(maxWidth: 420)

            VStack(spacing: 8) {
                ProgressView(value: vm.progress)
                    .progressViewStyle(.linear)
                    .frame(width: 360)

                statusLabel
            }
        }
        .padding(48)
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .onAppear {
            vm.onComplete = onComplete
            vm.start()
        }
    }

    @ViewBuilder
    private var statusLabel: some View {
        switch vm.state {
        case .checking:
            Text("Checking…").foregroundStyle(.secondary)
        case .downloading:
            Text("\(Int(vm.progress * 100))%").foregroundStyle(.secondary).monospacedDigit()
        case .done:
            Label("Ready", systemImage: "checkmark.circle.fill").foregroundStyle(.green)
        case .error(let msg):
            VStack(spacing: 8) {
                Label(msg, systemImage: "xmark.circle.fill").foregroundStyle(.red)
                Button("Retry", action: vm.retry).buttonStyle(.borderedProminent)
            }
        }
    }
}
