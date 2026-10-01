import SwiftUI

enum MotesTheme {
    static let accent = Color(hex: "#4F5BD5")
    static let teal = Color(hex: "#2DD4A8")
    static let cyan = Color(hex: "#38A1F3")
    static let purple = Color(hex: "#7B4FBF")
    static let magenta = Color(hex: "#C850C0")
    static let gradient = LinearGradient(colors: [accent, purple], startPoint: .topLeading, endPoint: .bottomTrailing)
    static let bgPrimary = Color(.systemBackground)
    static let bgSecondary = Color(.secondarySystemBackground)
    static let textPrimary = Color(.label)
    static let textSecondary = Color(.secondaryLabel)
    static let textMuted = Color(.tertiaryLabel)
    static let border = Color(.separator)
}

extension Color {
    init(hex: String) {
        let h = hex.trimmingCharacters(in: CharacterSet(charactersIn: "#"))
        var int: UInt64 = 0
        Scanner(string: h).scanHexInt64(&int)
        let r = Double((int >> 16) & 0xFF) / 255
        let g = Double((int >> 8) & 0xFF) / 255
        let b = Double(int & 0xFF) / 255
        self.init(red: r, green: g, blue: b)
    }
}
