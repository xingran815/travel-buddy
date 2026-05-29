import SwiftUI

struct ChipView: View {
    let label: String
    let isSelected: Bool
    var color: Color = .accentColor
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            Text(label)
                .font(.caption)
                .fontWeight(isSelected ? .semibold : .regular)
                .padding(.horizontal, 10)
                .padding(.vertical, 5)
                .background(isSelected ? color : color.opacity(0.12))
                .foregroundStyle(isSelected ? .white : color)
                .clipShape(Capsule())
        }
        .buttonStyle(.plain)
    }
}
