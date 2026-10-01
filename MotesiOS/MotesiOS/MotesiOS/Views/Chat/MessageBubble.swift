import SwiftUI

struct MessageBubble: View {
    let message: ChatMessage

    var body: some View {
        HStack(alignment: .top, spacing: 8) {
            if message.role == "user" {
                Spacer(minLength: 60)
                Text(message.content)
                    .font(.subheadline)
                    .padding(12)
                    .background(MotesTheme.accent)
                    .foregroundStyle(.white)
                    .clipShape(RoundedRectangle(cornerRadius: 16))
            } else if message.role == "tool" {
                Image("mascot-sm")
                    .resizable()
                    .frame(width: 20, height: 20)
                    .opacity(0.5)
                VStack(alignment: .leading, spacing: 2) {
                    Text("🔧 \(message.tool_name ?? "tool")")
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                    Text(message.content)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
                .padding(8)
                .background(Color.gray.opacity(0.08))
                .clipShape(RoundedRectangle(cornerRadius: 10))
                Spacer(minLength: 60)
            } else {
                Image("mascot-sm")
                    .resizable()
                    .frame(width: 24, height: 24)
                Text(LocalizedStringKey(message.content))
                    .font(.subheadline)
                    .textSelection(.enabled)
                Spacer(minLength: 40)
            }
        }
    }
}
