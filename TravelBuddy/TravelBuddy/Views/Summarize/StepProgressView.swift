import SwiftUI

struct StepProgressView: View {
    let currentStep: SummarizeStep?
    let progress: Double

    var body: some View {
        VStack(spacing: 16) {
            // Overall progress bar
            ProgressView(value: progress)
                .progressViewStyle(.linear)
                .tint(.accentColor)

            // Step indicators
            HStack(spacing: 0) {
                ForEach(SummarizeStep.allCases, id: \.self) { step in
                    stepDot(step)
                    if step != SummarizeStep.allCases.last {
                        Rectangle()
                            .fill(stepPassed(step) ? Color.accentColor : Color.gray.opacity(0.3))
                            .frame(height: 2)
                    }
                }
            }
        }
        .padding()
    }

    private func stepDot(_ step: SummarizeStep) -> some View {
        let passed  = stepPassed(step)
        let current = currentStep == step

        return VStack(spacing: 4) {
            ZStack {
                Circle()
                    .fill(passed ? Color.accentColor : Color.gray.opacity(0.2))
                    .frame(width: 28, height: 28)
                if current {
                    ProgressView()
                        .controlSize(.small)
                        .tint(.white)
                } else if passed {
                    Image(systemName: "checkmark")
                        .font(.caption.bold())
                        .foregroundStyle(.white)
                }
            }
            Text(step.label)
                .font(.system(size: 10))
                .foregroundStyle(passed || current ? .primary : .secondary)
        }
        .frame(maxWidth: .infinity)
    }

    private func stepPassed(_ step: SummarizeStep) -> Bool {
        guard let current = currentStep else { return step.rawValue < 4 }
        return step.rawValue < current.rawValue
    }
}
