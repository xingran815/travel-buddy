import SwiftUI

struct SummarizeView: View {
    @StateObject private var vm = SummarizeViewModel()
    @State private var lang = "en"

    var body: some View {
        VStack(spacing: 0) {
            // Input area
            VStack(alignment: .leading, spacing: 10) {
                Text("YouTube URL")
                    .font(.headline)
                HStack(spacing: 8) {
                    TextField("https://youtube.com/watch?v=…", text: $vm.url)
                        .textFieldStyle(.roundedBorder)
                    Picker("Lang", selection: $lang) {
                        Text("English").tag("en")
                        Text("Turkish").tag("tr")
                        Text("German").tag("de")
                        Text("French").tag("fr")
                        Text("Spanish").tag("es")
                    }
                    .frame(width: 110)
                    if case .loading = vm.state {
                        Button("Cancel", role: .cancel) { vm.cancel() }
                            .buttonStyle(.bordered)
                    } else {
                        Button {
                            vm.summarize(lang: lang)
                        } label: {
                            Label("Summarize", systemImage: "wand.and.stars")
                        }
                        .buttonStyle(.borderedProminent)
                        .disabled(vm.url.isEmpty)
                        .keyboardShortcut(.return, modifiers: [.command])
                    }
                }
            }
            .padding()

            Divider()

            // Content
            ScrollView {
                VStack(spacing: 16) {
                    switch vm.state {
                    case .idle:
                        idlePlaceholder
                    case .loading:
                        StepProgressView(currentStep: vm.currentStep, progress: vm.progress)
                            .padding()
                    case .error(let msg):
                        ErrorBannerView(message: msg) { vm.summarize(lang: lang) }
                    case .loaded:
                        if let result = vm.result {
                            SummaryResultView(result: result)
                        }
                    }
                }
            }
        }
        .navigationTitle("Video Summary")
    }

    private var idlePlaceholder: some View {
        VStack(spacing: 16) {
            Image(systemName: "play.rectangle.on.rectangle")
                .font(.system(size: 56))
                .foregroundStyle(.secondary)
            Text("Paste a YouTube URL to get started")
                .foregroundStyle(.secondary)
            Text("Audio is transcribed, translated if needed, and summarized using AI")
                .font(.caption)
                .foregroundStyle(.tertiary)
                .multilineTextAlignment(.center)
        }
        .padding(40)
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }
}
