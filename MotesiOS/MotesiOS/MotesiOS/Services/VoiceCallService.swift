import Foundation
import AVFoundation

@Observable
class VoiceCallService {
    var isConnected = false
    var status = "Disconnected"
    var transcripts: [(role: String, text: String)] = []

    private var webSocket: URLSessionWebSocketTask?
    private var audioPlayer: AVAudioPlayer?

    var onAudioReceived: ((Data) -> Void)?
    var onResponseDone: ((String) -> Void)?

    func connect(agentId: String, token: String, conversationId: String? = nil) {
        let baseURL = APIClient.shared.baseURL.replacingOccurrences(of: "http", with: "ws")
        guard let url = URL(string: "\(baseURL)/api/realtime-call/\(agentId)") else { return }
        let session = URLSession(configuration: .default)
        webSocket = session.webSocketTask(with: url)
        webSocket?.resume()

        status = "Connecting..."

        // Send auth
        var auth: [String: Any] = ["type": "auth", "token": token]
        if let cid = conversationId { auth["conversation_id"] = cid }
        if let data = try? JSONSerialization.data(withJSONObject: auth),
           let str = String(data: data, encoding: .utf8) {
            webSocket?.send(.string(str)) { _ in }
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
            case .failure:
                Task { @MainActor in
                    self.status = "Disconnected"
                    self.isConnected = false
                }
            }
        }
    }

    @MainActor
    private func handleEvent(type: String, obj: [String: Any]) {
        switch type {
        case "ready":
            isConnected = true
            status = "Connected"
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

    func sendAudio(base64: String) {
        let msg: [String: Any] = ["type": "audio", "data": base64]
        if let data = try? JSONSerialization.data(withJSONObject: msg),
           let str = String(data: data, encoding: .utf8) {
            webSocket?.send(.string(str)) { _ in }
        }
    }

    func playAudio(data: Data) {
        audioPlayer = try? AVAudioPlayer(data: data)
        audioPlayer?.delegate = nil
        audioPlayer?.play()
    }

    func disconnect() {
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
