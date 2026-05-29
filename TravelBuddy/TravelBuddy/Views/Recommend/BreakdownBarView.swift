import SwiftUI

struct BreakdownFactor: Identifiable, Equatable {
    let id: String
    let value: Double
    let color: Color
}

func breakdownFactors(from b: ScoreBreakdown) -> [BreakdownFactor] {
    let entries: [(String, Double?, Color)] = [
        ("Quality",   b.quality,   .green),
        ("Cuisine",   b.cuisine,   .pink),
        ("Sentiment", b.sentiment, .purple),
        ("Volume",    b.volume,    .cyan),
        ("Distance",  b.distance,  .orange),
        ("Cost",      b.cost,      .yellow),
        ("Recency",   b.recency,   .blue),
        ("Audience",  b.audience,  .mint),
        ("Aspects",   b.aspects,   .indigo),
        ("History",   b.history,   .gray),
    ]
    return entries
        .compactMap { id, value, color in
            guard let v = value, v > 0 else { return nil }
            return BreakdownFactor(id: id, value: v, color: color)
        }
        .sorted { $0.value > $1.value }
}

struct BreakdownBarView: View {
    let breakdown: ScoreBreakdown

    var body: some View {
        let factors = breakdownFactors(from: breakdown)
        let total = factors.reduce(0.0) { $0 + $1.value }

        VStack(alignment: .leading, spacing: 4) {
            Text("Score breakdown")
                .font(.caption2)
                .foregroundStyle(.secondary)
            GeometryReader { geo in
                HStack(spacing: 1) {
                    ForEach(factors) { factor in
                        RoundedRectangle(cornerRadius: 2)
                            .fill(factor.color)
                            .frame(width: total > 0
                                   ? geo.size.width * CGFloat(factor.value / total)
                                   : 0)
                    }
                }
            }
            .frame(height: 8)
            .clipShape(RoundedRectangle(cornerRadius: 4))

            FlowingLabels(factors: factors, total: total)
        }
    }
}

private struct FlowingLabels: View {
    let factors: [BreakdownFactor]
    let total: Double

    var body: some View {
        let columns = [GridItem(.adaptive(minimum: 70), spacing: 8)]
        LazyVGrid(columns: columns, alignment: .leading, spacing: 4) {
            ForEach(factors) { factor in
                HStack(spacing: 3) {
                    Circle().fill(factor.color).frame(width: 6, height: 6)
                    if total > 0 {
                        Text("\(factor.id) \(Int(round(factor.value / total * 100)))%")
                            .font(.system(size: 9))
                            .foregroundStyle(.secondary)
                    } else {
                        Text(factor.id).font(.system(size: 9))
                    }
                }
            }
        }
    }
}
