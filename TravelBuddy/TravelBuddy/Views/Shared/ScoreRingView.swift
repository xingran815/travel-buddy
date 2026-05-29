import SwiftUI

struct ScoreRingView: View {
    let score: Double
    var size: CGFloat = 56

    private var color: Color {
        if score >= 8.0 { return .green }
        if score >= 6.0 { return .orange }
        return .red
    }

    var body: some View {
        ZStack {
            Circle()
                .stroke(color.opacity(0.2), lineWidth: 5)
            Circle()
                .trim(from: 0, to: CGFloat(min(score / 10.0, 1.0)))
                .stroke(color, style: StrokeStyle(lineWidth: 5, lineCap: .round))
                .rotationEffect(.degrees(-90))
                .animation(.easeOut(duration: 0.6), value: score)
            Text(String(format: "%.1f", score))
                .font(.system(size: size * 0.28, weight: .bold, design: .rounded))
                .foregroundStyle(color)
        }
        .frame(width: size, height: size)
    }
}
