import Foundation

enum SummarizeStep: Int, CaseIterable {
    case downloading, transcribing, translating, summarizing

    var label: String {
        switch self {
        case .downloading:  return "Downloading"
        case .transcribing: return "Transcribing"
        case .translating:  return "Translating"
        case .summarizing:  return "Summarizing"
        }
    }
}

@MainActor
class SummarizeViewModel: ObservableObject {
    @Published var url: String = ""
    @Published var state: LoadState = .idle
    @Published var progress: Double = 0
    @Published var currentStep: SummarizeStep? = nil
    @Published var result: VideoResult? = nil
    @Published var errorMessage: String? = nil

    private var sseClient: SSEClient?

    func summarize(lang: String = "en") {
        guard !url.isEmpty else { return }
        state = .loading
        progress = 0
        result = nil
        errorMessage = nil
        currentStep = .downloading

        guard let encoded = try? JSONEncoder().encode(["url": url, "lang": lang]),
              let apiURL = URL(string: "\(BackendManager.baseURL)/api/summarize") else {
            state = .error("Invalid request"); return
        }

        var req = URLRequest(url: apiURL)
        req.httpMethod = "POST"
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        req.setValue("text/event-stream", forHTTPHeaderField: "Accept")
        req.httpBody = encoded

        let client = SSEClient()
        sseClient = client

        client.onEvent = { [weak self] payload in
            self?.handleEvent(payload)
        }
        client.onError = { [weak self] error in
            self?.state = .error(error.localizedDescription)
            self?.currentStep = nil
        }
        client.onComplete = { [weak self] in
            if case .loading = self?.state ?? .idle {
                self?.state = .loaded
            }
        }
        client.start(request: req)
    }

    func cancel() {
        sseClient?.cancel()
        sseClient = nil
        state = .idle
        currentStep = nil
        progress = 0
    }

    private func handleEvent(_ payload: String) {
        guard let data = payload.data(using: .utf8),
              let event = try? JSONDecoder().decode(SummarizeEvent.self, from: data) else { return }
        progress = event.progress
        switch event.step {
        case "downloading":   currentStep = .downloading
        case "transcribing":  currentStep = .transcribing
        case "translating":   currentStep = .translating
        case "summarizing":   currentStep = .summarizing
        case "summarize_done":
            if let d = event.data {
                result = VideoResult(
                    title: d.title ?? "Video",
                    videoId: d.video_id ?? "",
                    summary: d.summary ?? "",
                    translation: d.translation,
                    sourceLanguage: d.source_language ?? "??"
                )
            }
            state = .loaded
            currentStep = nil
        case "error":
            errorMessage = event.data?.message ?? "Unknown error"
            state = .error(errorMessage!)
            currentStep = nil
        default: break
        }
    }
}
