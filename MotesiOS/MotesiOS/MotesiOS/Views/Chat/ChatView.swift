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
                    ZStack(alignment: .bottomTrailing) {
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
                                scrollToBottom(proxy)
                            }
                            .onAppear {
                                scrollToBottom(proxy)
                            }
                        }

                        // Scroll to bottom button
                        Button {
                            // Trigger re-scroll by toggling a state
                            vm.scrollTrigger += 1
                        } label: {
                            Image(systemName: "arrow.down.circle.fill")
                                .font(.title2)
                                .foregroundStyle(.white)
                                .background(Circle().fill(Color.blue))
                        }
                        .padding(.trailing, 16)
                        .padding(.bottom, 8)
                    }
                }

                if let err = vm.error {
                    Text(err)
                        .font(.caption)
                        .foregroundStyle(.red)
                        .padding(.horizontal)
                }

                // Approval cards
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

                // Chat composer
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
                ToolbarItem(placement: .topBarLeading) {
                    Text("Motes")
                        .font(.headline)
                }
                ToolbarItem(placement: .topBarTrailing) {
                    HStack(spacing: 12) {
                        // Refresh button
                        Button {
                            Task { await vm.refreshThread() }
                        } label: {
                            Image(systemName: "arrow.clockwise")
                                .foregroundStyle(.secondary)
                        }
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
        .task {
            // Auto-refresh every 30s
            while !Task.isCancelled {
                try? await Task.sleep(for: .seconds(30))
                await vm.refreshThread()
            }
        }
    }

    private func scrollToBottom(_ proxy: ScrollViewProxy) {
        if let last = vm.messages.last {
            withAnimation { proxy.scrollTo(last.id, anchor: .bottom) }
        }
    }
}
