import SwiftUI

struct CallControls: View {
    var isMuted: Bool = false
    var isSpeaker: Bool = true
    var showCaptions: Bool = false
    var onMute: () -> Void = {}
    var onSpeaker: () -> Void = {}
    var onHangUp: () -> Void = {}
    var onCaptions: () -> Void = {}

    var body: some View {
        HStack(spacing: 24) {
            Button(action: onMute) {
                Image(systemName: isMuted ? "mic.slash.fill" : "mic.fill")
                    .font(.title3)
                    .frame(width: 50, height: 50)
                    .background(isMuted ? Color.red.opacity(0.2) : Color.gray.opacity(0.08))
                    .foregroundStyle(isMuted ? .red : .primary)
                    .clipShape(Circle())
            }

            Button(action: onSpeaker) {
                Image(systemName: isSpeaker ? "speaker.wave.3.fill" : "speaker.fill")
                    .font(.title3)
                    .frame(width: 50, height: 50)
                    .background(isSpeaker ? MotesTheme.accent.opacity(0.2) : Color.gray.opacity(0.08))
                    .foregroundStyle(isSpeaker ? MotesTheme.accent : .primary)
                    .clipShape(Circle())
            }

            Button(action: onHangUp) {
                Image(systemName: "phone.down.fill")
                    .font(.title2)
                    .foregroundStyle(.white)
                    .frame(width: 60, height: 60)
                    .background(Color.red)
                    .clipShape(Circle())
                    .shadow(color: .red.opacity(0.3), radius: 8)
            }

            Button(action: onCaptions) {
                Image(systemName: "captions.bubble.fill")
                    .font(.title3)
                    .frame(width: 50, height: 50)
                    .background(showCaptions ? MotesTheme.accent.opacity(0.2) : Color.gray.opacity(0.08))
                    .foregroundStyle(showCaptions ? MotesTheme.accent : .primary)
                    .clipShape(Circle())
            }
        }
    }
}
