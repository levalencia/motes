import SwiftUI

struct ChatView: View {
    @Bindable var vm: ChatViewModel

    var body: some View {
        NavigationStack {
            VStack(spacing: 0) {
                if vm.messages.isEmpty {
                    WelcomeView { text in
                        vm.input = text
                        Task { await vm.sendMessage() }
                    }
                } else {
                    ScrollViewReader { proxy in
                        ScrollView {
                            LazyVStack(alignment: .leading, spacing: 12) {
                                ForEach(vm.messages) { msg in
                                    MessageBubble(message: msg)
                                        .id(msg.id)
                                }
                            }
                            .padding(.horizontal, 12)
                            .padding(.vertical, 8)
                        }
                        .onChange(of: vm.messages.count) {
                            if let last = vm.messages.last {
                                withAnimation { proxy.scrollTo(last.id, anchor: .bottom) }
                            }
                        }
                    }
                }

                if let err = vm.error {
                    Text(err)
                        .font(.caption)
                        .foregroundStyle(.red)
                        .padding(.horizontal)
                }

                // Pending approval cards
                if !vm.pendingApprovals.isEmpty {
                    ScrollView(.horizontal, showsIndicators: false) {
                        HStack(spacing: 10) {
                            ForEach(vm.pendingApprovals) { approval in
                                ApprovalCardView(
                                    approval: approval,
                                    onApprove: { Task { await vm.approveItem(approval) } },
                                    onDeny: { Task { await vm.denyItem(approval) } }
                                )
                                .frame(width: 280)
                            }
                        }
                        .padding(.horizontal, 12)
                        .padding(.vertical, 6)
                    }
                }

                ChatComposer(
                    text: $vm.input,
                    isStreaming: vm.isStreaming,
                    isRecording: vm.speechRecognizer.isListening,
                    onSend: { Task { await vm.sendMessage() } },
                    onMicStart: { vm.startDictation() },
                    onMicStop: { vm.stopDictation() }
                )
            }
            .toolbar {
#if os(iOS)
                ToolbarItem(placement: .principal) {
                    HStack(spacing: 6) {
                        Image("mascot-sm")
                            .resizable()
                            .frame(width: 22, height: 22)
                        Text("Motes")
                            .font(.headline)
                    }
                }
#else
                ToolbarItem(placement: .automatic) {
                    HStack(spacing: 6) {
                        Image("mascot-sm")
                            .resizable()
                            .frame(width: 22, height: 22)
                        Text("Motes")
                            .font(.headline)
                    }
                }
#endif

#if os(iOS)
                ToolbarItem(placement: .topBarTrailing) {
                    HStack(spacing: 12) {
                        // Clear thread
                        if !vm.messages.isEmpty {
                            Button {
                                Task { await vm.clearThread() }
                            } label: {
                                Image(systemName: "trash")
                                    .foregroundStyle(.red.opacity(0.7))
                            }
                        }
                    }
                }
#else
                ToolbarItem(placement: .primaryAction) {
                    if !vm.messages.isEmpty {
                        Button {
                            Task { await vm.clearThread() }
                        } label: {
                            Image(systemName: "trash")
                                .foregroundStyle(.red.opacity(0.7))
                        }
                    }
                }
#endif
            }
        }
        .task { await vm.loadData() }
        .refreshable { await vm.refreshThread() }
    }
}
