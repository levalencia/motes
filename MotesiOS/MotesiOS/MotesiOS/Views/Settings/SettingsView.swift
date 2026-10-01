import SwiftUI

struct SettingsView: View {
    @Bindable var authVM: AuthViewModel
    @State private var voicePersonality = ""
    @State private var realtimeURL = ""
    @State private var realtimeKey = ""

    var body: some View {
        NavigationStack {
            Form {
                Section("Server") {
                    TextField("Tailscale URL", text: $authVM.serverURL)
                        .textContentType(.URL)
                        .font(.caption)
                }

                Section("Voice") {
                    TextField("Voice personality", text: $voicePersonality, axis: .vertical)
                        .lineLimit(2...4)
                        .font(.caption)
                    Text("e.g., \"Colombian paisa accent, warm and casual\"")
                        .font(.caption2)
                        .foregroundStyle(.tertiary)
                }

                Section("Realtime Voice Call") {
                    TextField("WebSocket URL", text: $realtimeURL)
                        .font(.caption)
                    SecureField("API Key", text: $realtimeKey)
                        .font(.caption)
                }

                Section("Account") {
                    HStack {
                        Text("Signed in as")
                        Spacer()
                        Text(AuthService.username)
                            .foregroundStyle(.secondary)
                    }
                    Button("Sign Out", role: .destructive) {
                        authVM.logout()
                    }
                }
            }
            .navigationTitle("Settings")
        }
    }
}
