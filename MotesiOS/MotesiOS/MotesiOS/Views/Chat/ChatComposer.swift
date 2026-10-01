import SwiftUI

struct ChatComposer: View {
    @Binding var text: String
    var isStreaming: Bool = false
    var onSend: () -> Void = {}
    var onMic: () -> Void = {}

    var body: some View {
        HStack(alignment: .bottom, spacing: 8) {
            TextField("Message Motes...", text: $text, axis: .vertical)
                .lineLimit(1...5)
                .padding(.horizontal, 12)
                .padding(.vertical, 10)
                .font(.subheadline)

            Button(action: onMic) {
                Image(systemName: "mic.fill")
                    .foregroundStyle(.secondary)
            }

            Button(action: onSend) {
                Image(systemName: "arrow.up")
                    .font(.subheadline.bold())
                    .foregroundStyle(.white)
                    .frame(width: 32, height: 32)
                    .background(
                        text.trimmingCharacters(in: .whitespaces).isEmpty
                            ? AnyShapeStyle(Color.gray.opacity(0.3))
                            : AnyShapeStyle(MotesTheme.gradient)
                    )
                    .clipShape(Circle())
            }
            .disabled(text.trimmingCharacters(in: .whitespaces).isEmpty || isStreaming)
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 8)
        .background(Color(uiColor: .secondarySystemBackground))
        .clipShape(RoundedRectangle(cornerRadius: 24))
        .shadow(color: .black.opacity(0.06), radius: 8, y: 2)
        .padding(.horizontal, 12)
        .padding(.bottom, 8)
    }
}
