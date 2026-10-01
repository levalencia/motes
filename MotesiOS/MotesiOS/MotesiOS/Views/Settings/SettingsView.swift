import SwiftUI

struct PersonalityPreset: Identifiable {
    let id: String
    let emoji: String
    let label: String
    let prompt: String
    let voice: String
}

let personalityPresets: [PersonalityPreset] = [
    .init(id: "friendly", emoji: "😊", label: "Friendly", prompt: "You are Motes, a warm and friendly AI assistant. You are helpful, encouraging, and use casual language. You remember things about the user and bring them up naturally.", voice: ""),
    .init(id: "professional", emoji: "💼", label: "Professional", prompt: "You are Motes, a concise professional assistant. Be direct, efficient, and actionable. Use bullet points when listing items. No small talk unless the user initiates.", voice: ""),
    .init(id: "paisa", emoji: "🇨🇴", label: "Paisa", prompt: "Eres Motes, un asistente personal amigable con estilo paisa colombiano. Siempre respondes en español con tono cálido, cercano y coloquial. Usas expresiones paisas cuando es natural.", voice: "Colombian paisa Spanish accent, warm and casual"),
    .init(id: "french", emoji: "🇫🇷", label: "Français", prompt: "Tu es Motes, un assistant personnel sympathique. Tu réponds toujours en français avec un ton chaleureux et professionnel.", voice: "Native French accent, warm and professional"),
    .init(id: "bilingual", emoji: "🌍", label: "ES/EN", prompt: "You are Motes, a bilingual assistant. Detect the user's language and respond in that language. Switch seamlessly between English and Spanish.", voice: ""),
    .init(id: "sarcastic", emoji: "😏", label: "Witty", prompt: "You are Motes, a witty assistant with a dry sense of humor. You're helpful but add clever observations and light sarcasm. Never mean — just entertaining.", voice: ""),
]

struct SettingsView: View {
    @Bindable var authVM: AuthViewModel
    @State private var voicePersonality = ""
    @State private var realtimeURL = ""
    @State private var realtimeKey = ""
    @State private var systemPrompt = ""
    @State private var agentName = "Motes"
    @State private var agentId = ""
    @State private var saved = false
    @State private var selectedPreset = ""

    var body: some View {
        NavigationStack {
            Form {
                Section("🎭 Personality") {
                    // Preset grid
                    LazyVGrid(columns: [
                        GridItem(.flexible()),
                        GridItem(.flexible()),
                        GridItem(.flexible()),
                    ], spacing: 8) {
                        ForEach(personalityPresets) { preset in
                            Button {
                                systemPrompt = preset.prompt
                                if !preset.voice.isEmpty { voicePersonality = preset.voice }
                                selectedPreset = preset.id
                            } label: {
                                VStack(spacing: 4) {
                                    Text(preset.emoji).font(.title2)
                                    Text(preset.label).font(.caption2).lineLimit(1)
                                }
                                .frame(maxWidth: .infinity)
                                .padding(.vertical, 8)
                                .background(selectedPreset == preset.id ? Color.blue.opacity(0.2) : Color.gray.opacity(0.1))
                                .clipShape(RoundedRectangle(cornerRadius: 8))
                                .overlay(
                                    RoundedRectangle(cornerRadius: 8)
                                        .stroke(selectedPreset == preset.id ? Color.blue : Color.clear, lineWidth: 1.5)
                                )
                            }
                            .buttonStyle(.plain)
                        }
                    }
                    .padding(.vertical, 4)

                    TextField("Agent name", text: $agentName)
                        .font(.subheadline)

                    TextField("System prompt", text: $systemPrompt, axis: .vertical)
                        .lineLimit(3...6)
                        .font(.caption)

                    TextField("Voice accent", text: $voicePersonality, axis: .vertical)
                        .lineLimit(1...2)
                        .font(.caption)
                    Text("Controls how Motes sounds on calls")
                        .font(.caption2)
                        .foregroundStyle(.tertiary)

                    Button {
                        Task { await savePersonality() }
                    } label: {
                        HStack {
                            Text("Save Personality")
                            if saved {
                                Image(systemName: "checkmark.circle.fill")
                                    .foregroundStyle(.green)
                            }
                        }
                    }
                }

                Section("Server") {
                    TextField("Tailscale URL", text: $authVM.serverURL)
                        .textContentType(.URL)
                        .font(.caption)
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
            .task { await loadPersonality() }
        }
    }

    func loadPersonality() async {
        do {
            let agents: [Agent] = try await APIClient.shared.get("/api/agents")
            if let first = agents.first {
                agentId = first.id
                // Load personality (simple dict response)
                let url = URL(string: "\(APIClient.shared.baseURL)/api/agents/\(agentId)/personality")!
                var req = URLRequest(url: url)
                if let t = APIClient.shared.token {
                    req.setValue("Bearer \(t)", forHTTPHeaderField: "Authorization")
                }
                let (data, _) = try await APIClient.shared.session.data(for: req)
                if let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any] {
                    agentName = json["name"] as? String ?? "Motes"
                    systemPrompt = json["system_prompt"] as? String ?? ""
                    voicePersonality = json["voice_personality"] as? String ?? ""
                }
            }
        } catch { /* ignore load errors */ }
    }

    func savePersonality() async {
        do {
            if !agentId.isEmpty {
                let url = URL(string: "\(APIClient.shared.baseURL)/api/agents/\(agentId)/personality")!
                var req = URLRequest(url: url)
                req.httpMethod = "PUT"
                req.setValue("application/json", forHTTPHeaderField: "Content-Type")
                if let t = APIClient.shared.token {
                    req.setValue("Bearer \(t)", forHTTPHeaderField: "Authorization")
                }
                req.httpBody = try JSONSerialization.data(withJSONObject: [
                    "name": agentName,
                    "system_prompt": systemPrompt,
                ])
                let _ = try await APIClient.shared.session.data(for: req)
            }
            // Save voice personality
            let vpURL = URL(string: "\(APIClient.shared.baseURL)/api/voice/voice-personality")!
            var vpReq = URLRequest(url: vpURL)
            vpReq.httpMethod = "POST"
            vpReq.setValue("application/json", forHTTPHeaderField: "Content-Type")
            if let t = APIClient.shared.token {
                vpReq.setValue("Bearer \(t)", forHTTPHeaderField: "Authorization")
            }
            vpReq.httpBody = try JSONSerialization.data(withJSONObject: ["personality": voicePersonality])
            let _ = try await APIClient.shared.session.data(for: vpReq)

            saved = true
            DispatchQueue.main.asyncAfter(deadline: .now() + 2) { saved = false }
        } catch { /* ignore */ }
    }
}
