import SwiftUI

struct MessageBubble: View {
    let message: ChatMessage

    var body: some View {
        switch message.resolvedType {
        case "system":
            systemBubble
        case "proactive":
            proactiveBubble
        case "call":
            callBubble
        default:
            chatBubble
        }
    }

    // MARK: - Chat (default)
    @ViewBuilder
    private var chatBubble: some View {
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
                        .lineLimit(3)
                }
                .padding(8)
                .background(Color.gray.opacity(0.08))
                .clipShape(RoundedRectangle(cornerRadius: 10))
                Spacer(minLength: 60)
            } else {
                Image("mascot-sm")
                    .resizable()
                    .frame(width: 24, height: 24)
                    .padding(.top, 2)
                MarkdownView(content: message.content)
                Spacer(minLength: 20)
            }
        }
    }

    // MARK: - Call transcript
    @ViewBuilder
    private var callBubble: some View {
        HStack(alignment: .top, spacing: 8) {
            if message.role == "user" {
                Spacer(minLength: 60)
                HStack(spacing: 4) {
                    Text("📞")
                        .font(.caption)
                    Text(message.content)
                        .font(.subheadline)
                }
                .padding(12)
                .background(Color.green.opacity(0.15))
                .foregroundStyle(.primary)
                .clipShape(RoundedRectangle(cornerRadius: 16))
            } else {
                Image(systemName: "phone.fill")
                    .foregroundStyle(.green)
                    .font(.caption)
                    .frame(width: 24, height: 24)
                    .padding(.top, 2)
                VStack(alignment: .leading, spacing: 2) {
                    Text("Voice call")
                        .font(.caption2)
                        .foregroundStyle(.green)
                    MarkdownView(content: message.content)
                }
                Spacer(minLength: 20)
            }
        }
    }

    // MARK: - Proactive insight
    @ViewBuilder
    private var proactiveBubble: some View {
        HStack(alignment: .top, spacing: 8) {
            Image(systemName: "lightbulb.fill")
                .foregroundStyle(.orange)
                .font(.caption)
                .frame(width: 24, height: 24)
                .padding(.top, 2)
            VStack(alignment: .leading, spacing: 2) {
                Text("Proactive Insight")
                    .font(.caption2)
                    .foregroundStyle(.orange)
                MarkdownView(content: message.content)
            }
            .padding(10)
            .background(Color.orange.opacity(0.08))
            .clipShape(RoundedRectangle(cornerRadius: 14))
            Spacer(minLength: 20)
        }
    }

    // MARK: - System message
    @ViewBuilder
    private var systemBubble: some View {
        HStack {
            Spacer()
            Text(message.content)
                .font(.caption)
                .foregroundStyle(.gray)
                .multilineTextAlignment(.center)
                .padding(.vertical, 4)
            Spacer()
        }
    }
}
