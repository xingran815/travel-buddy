import Foundation
import SwiftUI

struct AppCategory: Codable, Identifiable {
    let id: String
    let name_en: String
    let name_tr: String
    let google_types: [String]

    var displayName: String { name_en }

    var sfSymbol: String {
        switch id {
        case "food":      return "fork.knife"
        case "sights":    return "binoculars.fill"
        case "museums":   return "building.columns.fill"
        case "nature":    return "tree.fill"
        case "shopping":  return "bag.fill"
        case "nightlife": return "moon.stars.fill"
        case "family":    return "figure.2.and.child.holdinghands"
        case "lodging":   return "bed.double.fill"
        case "wellness":  return "figure.mind.and.body"
        default:          return "mappin.circle.fill"
        }
    }

    var accentColor: String {
        switch id {
        case "food":      return "orange"
        case "sights":    return "blue"
        case "museums":   return "purple"
        case "nature":    return "green"
        case "shopping":  return "pink"
        case "nightlife": return "indigo"
        case "family":    return "yellow"
        case "lodging":   return "teal"
        case "wellness":  return "mint"
        default:          return "gray"
        }
    }

    var color: Color {
        switch accentColor {
        case "orange": return .orange
        case "blue":   return .blue
        case "purple": return .purple
        case "green":  return .green
        case "pink":   return .pink
        case "indigo": return .indigo
        case "yellow": return .yellow
        case "teal":   return .teal
        case "mint":   return .mint
        default:       return .accentColor
        }
    }
}
