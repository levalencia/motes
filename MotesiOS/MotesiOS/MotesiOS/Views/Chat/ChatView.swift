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

                ChatComposer(
                    text: $vm.input,
                    isStreaming: vm.isStreaming,
                    onSend: { Task { await vm.sendMessage() } }
                )
            }
#if os(macOS)
            .navigationTitle("Motes")
#endif
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
                    if !vm.agentId.isEmpty {
                        NavigationLink(destination: CallView(agentId: vm.agentId)) {
                            Image(systemName: "phone.fill")
                                .foregroundStyle(Color.green)
                        }
                    }
                }
#else
                ToolbarItem(placement: .primaryAction) {
                    if !vm.agentId.isEmpty {
                        NavigationLink(destination: CallView(agentId: vm.agentId)) {
                            Image(systemName: "phone.fill")
                                .foregroundStyle(Color.green)
                        }
                    }
                }
#endif
            }
        }
        .task { await vm.loadData() }
    }
}
