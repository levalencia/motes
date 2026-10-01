import SwiftUI

struct WelcomeView: View {
    var onSend: (String) -> Void = { _ in }

    let suggestions = [
        ("📧", "Show me my unread emails"),
        ("📅", "What's on my calendar today?"),
        ("🔍", "Search the web for AI news"),
        ("🌤️", "What's the weather in Brussels?"),
    ]

    var body: some View {
        VStack(spacing: 12) {
            Spacer()
            MascotView(size: 90)
            Text("Hi, I'm Motes")
                .font(.title2.bold())
            Text("Your AI assistant for deeper thinking, faster answers and bigger ideas.")
                .font(.caption)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
                .padding(.horizontal, 32)

            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: 8) {
                    ForEach(suggestions, id: \.1) { icon, text in
                        Button {
                            onSend(text)
                        } label: {
                            HStack(spacing: 6) {
                                Text(icon)
                                Text(text)
                                    .font(.caption)
                            }
                            .padding(.horizontal, 12)
                            .padding(.vertical, 10)
                            .background(Color(.tertiarySystemBackground))
                            .clipShape(RoundedRectangle(cornerRadius: 12))
                        }
                        .buttonStyle(.plain)
                    }
                }
                .padding(.horizontal, 16)
            }
            Spacer()
        }
    }
}
