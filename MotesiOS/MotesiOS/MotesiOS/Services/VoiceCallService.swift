import Foundation
import AVFoundation

@Observable
class VoiceCallService {
    var isConnected = false
    var status = "Disconnected"
    var transcripts: [(role: String, text: String)] = []

    private var webSocket: URLSessionWebSocketTask?
    private var audioPlayer: AVAudioPlayer?

    // Reconnect state
    private var lastAgentId = ""
    private var lastToken = ""
    private var lastConversationId: String?
    private var reconnectAttempts = 0
    private let maxReconnectAttempts = 3

    var onReady: (() -> Void)?
    var onAudioReceived: ((Data) -> Void)?
    var onResponseDone: ((String) -> Void)?
    var onError: ((String) -> Void)?

    func connect(agentId: String, token: String, conversationId: String? = nil) {
        // Save for reconnect
        lastAgentId = agentId
        lastToken = token
        lastConversationId = conversationId
        reconnectAttempts = 0

        doConnect(agentId: agentId, token: token, conversationId: conversationId)
    }

    private func doConnect(agentId: String, token: String, conversationId: String?) {
        let baseURL = APIClient.shared.baseURL.replacingOccurrences(of: "http://", with: "ws://")
            .replacingOccurrences(of: "https://", with: "wss://")
        guard let url = URL(string: "\(baseURL)/api/realtime-call/\(agentId)") else {
            onError?("Invalid server URL")
            return
        }

        let config = URLSessionConfiguration.default
        config.timeoutIntervalForRequest = 30
        let session = URLSession(configuration: config)
        webSocket = session.webSocketTask(with: url)
        webSocket?.resume()

        status = "Connecting..."

        // Send auth
        var auth: [String: Any] = ["type": "auth", "token": token]
        if let cid = conversationId { auth["conversation_id"] = cid }
        if let data = try? JSONSerialization.data(withJSONObject: auth),
           let str = String(data: data, encoding: .utf8) {
            webSocket?.send(.string(str)) { [weak self] error in
                if let error {
                    Task { @MainActor in
                        self?.status = "Auth failed"
                        self?.onError?("Send auth failed: \(error.localizedDescription)")
                    }
                }
            }
        }

        receiveMessages()
    }

    private func receiveMessages() {
        webSocket?.receive { [weak self] result in
            guard let self else { return }
            switch result {
            case .success(let msg):
                if case .string(let text) = msg,
                   let data = text.data(using: .utf8),
                   let obj = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
                   let type = obj["type"] as? String {
                    Task { @MainActor in
                        self.handleEvent(type: type, obj: obj)
                    }
                }
                self.receiveMessages()
            case .failure(let error):
                Task { @MainActor in
                    self.handleDisconnect(error: error)
                }
            }
        }
    }

    @MainActor
    private func handleDisconnect(error: Error) {
        let wasConnected = isConnected
        isConnected = false

        // Auto-reconnect if was connected and haven't exceeded attempts
        if wasConnected && reconnectAttempts < maxReconnectAttempts {
            reconnectAttempts += 1
            status = "Reconnecting (\(reconnectAttempts)/\(maxReconnectAttempts))..."
            // Wait a moment then reconnect
            DispatchQueue.main.asyncAfter(deadline: .now() + 1.0) {
                self.doConnect(
                    agentId: self.lastAgentId,
                    token: self.lastToken,
                    conversationId: self.lastConversationId
                )
            }
        } else {
            status = "Disconnected"
            onError?(error.localizedDescription)
        }
    }

    @MainActor
    private func handleEvent(type: String, obj: [String: Any]) {
        switch type {
        case "ready":
            isConnected = true
            reconnectAttempts = 0
            status = "Connected"
            onReady?()
        case "audio_wav":
            if let b64 = obj["data"] as? String, let data = Data(base64Encoded: b64) {
                status = "Speaking..."
                playAudio(data: data)
            }
        case "response_done":
            if let text = obj["text"] as? String {
                transcripts.append((role: "assistant", text: text))
                onResponseDone?(text)
            }
            status = "Listening..."
        case "user_transcript":
            if let text = obj["text"] as? String {
                transcripts.append((role: "user", text: text))
            }
        case "error":
            if let msg = obj["message"] as? String, !msg.lowercased().contains("buffer too small") {
                status = "Error: \(msg)"
            }
        default: break
        }
    }

    func sendAudio(base64: String, sampleRate: Double = 24000) {
        let msg: [String: Any] = ["type": "audio", "data": base64, "format": "pcm16", "sample_rate": "\(Int(sampleRate))"]
        if let data = try? JSONSerialization.data(withJSONObject: msg),
           let str = String(data: data, encoding: .utf8) {
            webSocket?.send(.string(str)) { error in
                if let error {
                    print("[Motes] Audio send error: \(error.localizedDescription)")
                }
            }
        }
    }

    func playAudio(data: Data) {
        audioPlayer = try? AVAudioPlayer(data: data)
        audioPlayer?.play()
    }

    func disconnect() {
        reconnectAttempts = maxReconnectAttempts // Prevent auto-reconnect
        let end: [String: String] = ["type": "end"]
        if let data = try? JSONSerialization.data(withJSONObject: end),
           let str = String(data: data, encoding: .utf8) {
            webSocket?.send(.string(str)) { _ in }
        }
        webSocket?.cancel(with: .normalClosure, reason: nil)
        webSocket = nil
        isConnected = false
        status = "Disconnected"
    }
}
