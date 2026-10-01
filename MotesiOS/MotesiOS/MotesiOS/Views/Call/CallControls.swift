import SwiftUI

struct CallControls: View {
    var isMuted: Bool = false
    var showCaptions: Bool = false
    var onMute: () -> Void = {}
    var onHangUp: () -> Void = {}
    var onCaptions: () -> Void = {}

    var body: some View {
        HStack(spacing: 32) {
            Button(action: onMute) {
                Image(systemName: isMuted ? "mic.slash.fill" : "mic.fill")
                    .font(.title2)
                    .frame(width: 56, height: 56)
                    .background(Color.gray.opacity(0.08))
                    .clipShape(Circle())
            }

            Button(action: onHangUp) {
                Image(systemName: "phone.down.fill")
                    .font(.title2)
                    .foregroundStyle(.white)
                    .frame(width: 64, height: 64)
                    .background(Color.red)
                    .clipShape(Circle())
                    .shadow(color: .red.opacity(0.3), radius: 8)
            }

            Button(action: onCaptions) {
                Image(systemName: "captions.bubble.fill")
                    .font(.title2)
                    .frame(width: 56, height: 56)
                    .background(showCaptions ? MotesTheme.accent : Color.gray.opacity(0.08))
                    .foregroundStyle(showCaptions ? .white : .primary)
                    .clipShape(Circle())
            }
        }
    }
}
