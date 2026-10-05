import Foundation
import AVFoundation

@Observable
class VoiceCallService {
    var isConnected = false
    var status = "Disconnected"
    var transcripts: [(role: String, text: String)] = []

    private var webSocket: URLSessionWebSocketTask?
    private var urlSession: URLSession?
    private let maxReconnectAttempts = 3
    private var reconnectAttempts = 0
    private var lastAgentId = ""
    private var lastToken = ""
    private var lastConversationId: String?
    private var intentionalDisconnect = false
    private var keepAliveTimer: Timer?

    var onAudioReceived: ((Data) -> Void)?
    var onReady: (() -> Void)?
    var onError: ((String) -> Void)?
    var onResponseDone: ((String) -> Void)?

    func connect(agentId: String, token: String, conversationId: String? = nil) {
        // Save for reconnect
        lastAgentId = agentId
        lastToken = token
        lastConversationId = conversationId
        reconnectAttempts = 0
        intentionalDisconnect = false
        doConnect(agentId: agentId, token: token, conversationId: conversationId)
    }

    private func doConnect(agentId: String, token: String, conversationId: String?) {
        let baseURL = APIClient.shared.baseURL
            .replacingOccurrences(of: "https://", with: "wss://")
            .replacingOccurrences(of: "http://", with: "ws://")
        let urlStr = "\(baseURL)/api/realtime-call/\(agentId)"

        guard let url = URL(string: urlStr) else {
            status = "Invalid URL"
            return
        }

        let session = URLSession(configuration: .default)
        urlSession = session
        let ws = session.webSocketTask(with: url)
        webSocket = ws
        ws.resume()

        status = "Connecting..."

        // Send auth
        let auth: [String: Any] = [
            "type": "auth",
            "token": token,
            "agent_id": agentId,
            "conversation_id": conversationId ?? "",
        ]
        if let data = try? JSONSerialization.data(withJSONObject: auth),
           let str = String(data: data, encoding: .utf8) {
            ws.send(.string(str)) { [weak self] error in
                if let error {
                    Task { @MainActor in
                        self?.status = "Auth failed"
                        self?.onError?("Send auth failed: \(error.localizedDescription)")
                    }
                }
            }
        }

        receiveMessages()
        startKeepAlive()
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
        stopKeepAlive()

        // Only reconnect if NOT intentional and was a screen-sleep type disconnect
        // Don't reconnect on normal errors during active call — it causes duplicate sessions
        if wasConnected && !intentionalDisconnect && reconnectAttempts < maxReconnectAttempts {
            let errorMsg = error.localizedDescription.lowercased()
            // Only reconnect on connection-abort type errors (screen sleep)
            let isConnectionAbort = errorMsg.contains("abort")
                || errorMsg.contains("connection reset")
                || errorMsg.contains("network")
            if isConnectionAbort {
                reconnectAttempts += 1
                status = "Reconnecting (\(reconnectAttempts)/\(maxReconnectAttempts))..."
                DispatchQueue.main.asyncAfter(deadline: .now() + 2.0) {
                    self.doConnect(
                        agentId: self.lastAgentId,
                        token: self.lastToken,
                        conversationId: self.lastConversationId
                    )
                }
                return
            }
        }

        status = "Disconnected"
        if !intentionalDisconnect {
            onError?(error.localizedDescription)
        }
    }

    private func startKeepAlive() {
        stopKeepAlive()
        // Send ping every 20 seconds to keep WebSocket alive
        keepAliveTimer = Timer.scheduledTimer(withTimeInterval: 20.0, repeats: true) { [weak self] _ in
            self?.webSocket?.sendPing { error in
                if let error {
                    print("[Motes] WebSocket ping failed: \(error.localizedDescription)")
                }
            }
        }
    }

    private func stopKeepAlive() {
        keepAliveTimer?.invalidate()
        keepAliveTimer = nil
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
            if let b64 = obj["data"] as? String,
               let data = Data(base64Encoded: b64) {
                onAudioReceived?(data)
            }
        case "response_transcript":
            if let text = obj["text"] as? String {
                // Update last assistant transcript
                if let last = transcripts.last, last.role == "assistant" {
                    transcripts[transcripts.count - 1] = (role: "assistant", text: text)
                } else {
                    transcripts.append((role: "assistant", text: text))
                }
            }
        case "response_done":
            if let text = obj["text"] as? String, !text.isEmpty {
                onResponseDone?(text)
            }
        case "user_transcript":
            if let text = obj["text"] as? String, !text.isEmpty {
                transcripts.append((role: "user", text: text))
            }
        case "error":
            let msg = obj["message"] as? String ?? "Unknown error"
            onError?(msg)
        default:
            break
        }
    }

    func sendAudio(base64: String, sampleRate: Double = 24000) {
        let msg: [String: Any] = [
            "type": "audio",
            "data": base64,
            "format": "pcm16",
            "sample_rate": "\(Int(sampleRate))",
        ]
        if let data = try? JSONSerialization.data(withJSONObject: msg),
           let str = String(data: data, encoding: .utf8) {
            webSocket?.send(.string(str)) { error in
                if let error {
                    print("[Motes] Audio send error: \(error.localizedDescription)")
                }
            }
        }
    }

    func disconnect() {
        intentionalDisconnect = true
        stopKeepAlive()
        webSocket?.cancel(with: .goingAway, reason: nil)
        webSocket = nil
        isConnected = false
        status = "Disconnected"
    }
}
