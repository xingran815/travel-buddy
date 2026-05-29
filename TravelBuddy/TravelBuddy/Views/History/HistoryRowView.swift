import SwiftUI

struct HistoryRowView: View {
    let event: HistoryEvent

    var body: some View {
        HStack(spacing: 10) {
            Image(systemName: icon)
                .foregroundStyle(color)
                .frame(width: 28)
            VStack(alignment: .leading, spacing: 2) {
                Text(event.place_id)
                    .font(.body)
                    .lineLimit(1)
                Text(event.action.capitalized)
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
            Spacer()
            VStack(alignment: .trailing, spacing: 2) {
                Text(Date(timeIntervalSince1970: event.ts), style: .date)
                    .font(.caption2)
                    .foregroundStyle(.secondary)
                if let rating = event.rating {
                    HStack(spacing: 2) {
                        Image(systemName: "star.fill")
                            .font(.system(size: 9))
                            .foregroundStyle(.yellow)
                        Text("\(rating)")
                            .font(.caption2)
                    }
                }
            }
        }
        .padding(.vertical, 4)
    }

    private var icon: String {
        switch event.action {
        case "liked":    return "hand.thumbsup.fill"
        case "disliked": return "hand.thumbsdown.fill"
        case "visited":  return "checkmark.seal.fill"
        default:         return "clock"
        }
    }

    private var color: Color {
        switch event.action {
        case "liked":    return .green
        case "disliked": return .red
        case "visited":  return .blue
        default:         return .secondary
        }
    }
}
