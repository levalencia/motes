import SwiftUI

struct CallView: View {
    let agentId: String
    var conversationId: String? = nil
    @State private var vm = CallViewModel()

    var body: some View {
        VStack(spacing: 0) {
            Spacer()

            MascotView(size: 120)
                .scaleEffect(vm.isSpeaking ? 1.1 : 1.0)
                .animation(.easeInOut(duration: 0.5).repeatForever(autoreverses: true), value: vm.isSpeaking)

            Text("Motes")
                .font(.title2.bold())
                .padding(.top, 8)

            Text(vm.status)
                .font(.caption)
                .foregroundStyle(.secondary)
                .padding(.top, 2)

            if vm.isConnected {
                Text(vm.formattedDuration)
                    .font(.caption.monospacedDigit())
                    .foregroundStyle(.tertiary)
                    .padding(.top, 4)
            }

            if vm.showCaptions, !vm.transcripts.isEmpty {
                VStack(spacing: 4) {
                    ForEach(vm.transcripts.suffix(3), id: \.text) { t in
                        Text(t.role == "user" ? "\"\(t.text)\"" : t.text)
                            .font(.caption)
                            .foregroundStyle(t.role == "user" ? .secondary : .primary)
                    }
                }
                .padding(.horizontal, 24)
                .padding(.top, 16)
            }

            Spacer()

            CallControls(
                showCaptions: vm.showCaptions,
                onMute: { vm.isListening.toggle() },
                onHangUp: { vm.hangUp() },
                onCaptions: { vm.showCaptions.toggle() }
            )
            .padding(.bottom, 48)
        }
        .onAppear { vm.startCall(agentId: agentId, conversationId: conversationId) }
        .onDisappear { vm.hangUp() }
    }
}
