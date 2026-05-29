import SwiftUI

struct SummaryResultView: View {
    let result: VideoResult
    @State private var tab = 0
    @State private var copied = false

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            // Title
            Text(result.title)
                .font(.title3.bold())
                .lineLimit(2)

            HStack {
                Label("Language: \(result.sourceLanguage.uppercased())",
                      systemImage: "globe")
                    .font(.caption)
                    .foregroundStyle(.secondary)
                Spacer()
                Button {
                    let text = tab == 0 ? result.summary : (result.translation ?? "")
                    NSPasteboard.general.clearContents()
                    NSPasteboard.general.setString(text, forType: .string)
                    copied = true
                    DispatchQueue.main.asyncAfter(deadline: .now() + 2) { copied = false }
                } label: {
                    Label(copied ? "Copied!" : "Copy", systemImage: copied ? "checkmark" : "doc.on.doc")
                        .font(.caption)
                }
                .buttonStyle(.bordered)
                .animation(.easeInOut, value: copied)
            }

            Picker("Tab", selection: $tab) {
                Text("Summary").tag(0)
                if result.translation != nil {
                    Text("Full Translation").tag(1)
                }
            }
            .pickerStyle(.segmented)

            ScrollView {
                Text(tab == 0 ? result.summary : (result.translation ?? ""))
                    .font(.body)
                    .textSelection(.enabled)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .padding()
            }
            .background(.quinary)
            .clipShape(RoundedRectangle(cornerRadius: 8))
        }
        .padding()
    }
}
