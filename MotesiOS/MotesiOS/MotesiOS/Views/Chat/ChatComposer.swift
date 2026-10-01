import SwiftUI

struct ChatComposer: View {
    @Binding var text: String
    var isStreaming: Bool = false
    var isRecording: Bool = false
    var onSend: () -> Void = {}
    var onMicStart: () -> Void = {}
    var onMicStop: () -> Void = {}

    var body: some View {
        HStack(alignment: .bottom, spacing: 8) {
            TextField("Message Motes...", text: $text, axis: .vertical)
                .lineLimit(1...5)
                .padding(.horizontal, 12)
                .padding(.vertical, 10)
                .font(.subheadline)

            // Mic button — tap to toggle recording
            Button(action: {
                if isRecording {
                    onMicStop()
                } else {
                    onMicStart()
                }
            }) {
                Image(systemName: isRecording ? "mic.fill" : "mic")
                    .foregroundStyle(isRecording ? MotesTheme.accent : .secondary)
                    .symbolEffect(.pulse, isActive: isRecording)
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
        .background(Color.gray.opacity(0.1))
        .clipShape(RoundedRectangle(cornerRadius: 24))
        .shadow(color: .black.opacity(0.06), radius: 8, y: 2)
        .padding(.horizontal, 12)
        .padding(.bottom, 8)
    }
}
