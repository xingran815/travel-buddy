import SwiftUI

struct PlannerView: View {
    var body: some View {
        VStack(spacing: 20) {
            Image(systemName: "map.fill")
                .font(.system(size: 72))
                .foregroundStyle(.secondary)
            Text("Trip Planner")
                .font(.largeTitle.bold())
            Text("Coming Soon")
                .font(.title2)
                .foregroundStyle(.secondary)
            Text("AI-powered multi-day itinerary generation based on your videos and recommendations.")
                .font(.body)
                .foregroundStyle(.tertiary)
                .multilineTextAlignment(.center)
                .frame(maxWidth: 360)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .navigationTitle("Trip Planner")
    }
}
