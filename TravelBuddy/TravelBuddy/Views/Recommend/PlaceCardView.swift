import SwiftUI

struct PlaceCardView: View {
    let place: Place
    var onLike: (() -> Void)? = nil
    var onVisit: (() -> Void)? = nil

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            // Header row
            HStack(alignment: .top) {
                VStack(alignment: .leading, spacing: 2) {
                    Text(place.name)
                        .font(.headline)
                        .lineLimit(1)
                    if let address = place.address {
                        Text(address)
                            .font(.caption)
                            .foregroundStyle(.secondary)
                            .lineLimit(1)
                    }
                    starRow
                }
                Spacer()
                if let score = place.score {
                    ScoreRingView(score: score)
                }
            }

            if let breakdown = place.score_breakdown {
                BreakdownBarView(breakdown: breakdown)
            }

            if let rationale = place.llm_rationale, !rationale.isEmpty {
                Text(rationale)
                    .font(.caption2)
                    .italic()
                    .foregroundStyle(.secondary)
                    .lineLimit(3)
            }

            if let summary = place.summary {
                Text(summary)
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .lineLimit(3)
            }

            prosConsRow

            // Action buttons
            HStack(spacing: 8) {
                Button { onLike?() } label: {
                    Label("Like", systemImage: "hand.thumbsup")
                        .font(.caption)
                }
                .buttonStyle(.bordered)

                Button { onVisit?() } label: {
                    Label("Visited", systemImage: "checkmark.seal")
                        .font(.caption)
                }
                .buttonStyle(.bordered)

                if let website = place.website, let url = URL(string: website) {
                    Link(destination: url) {
                        Label("Website", systemImage: "globe")
                            .font(.caption)
                    }
                    .buttonStyle(.bordered)
                }
            }
        }
        .padding(12)
        .background(.background)
        .clipShape(RoundedRectangle(cornerRadius: 10))
        .shadow(color: .black.opacity(0.07), radius: 4, y: 2)
    }

    private var starRow: some View {
        HStack(spacing: 4) {
            if let r = place.rating {
                Image(systemName: "star.fill").foregroundStyle(.yellow).font(.caption)
                Text(String(format: "%.1f", r)).font(.caption)
            }
            if let n = place.user_ratings_total {
                Text("(\(n))").font(.caption).foregroundStyle(.secondary)
            }
            if let p = place.price_level {
                Text(String(repeating: "$", count: p))
                    .font(.caption).foregroundStyle(.green)
            }
        }
    }

    private var prosConsRow: some View {
        HStack(alignment: .top, spacing: 12) {
            if let pros = place.pros, !pros.isEmpty {
                VStack(alignment: .leading, spacing: 2) {
                    ForEach(pros.prefix(2), id: \.self) { p in
                        Label(p, systemImage: "plus.circle.fill")
                            .font(.caption2)
                            .foregroundStyle(.green)
                            .lineLimit(1)
                    }
                }
            }
            if let cons = place.cons, !cons.isEmpty {
                VStack(alignment: .leading, spacing: 2) {
                    ForEach(cons.prefix(2), id: \.self) { c in
                        Label(c, systemImage: "minus.circle.fill")
                            .font(.caption2)
                            .foregroundStyle(.red)
                            .lineLimit(1)
                    }
                }
            }
        }
    }
}
