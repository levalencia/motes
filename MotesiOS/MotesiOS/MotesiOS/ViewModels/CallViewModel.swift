import Foundation
import AVFoundation

@Observable
class CallViewModel {
    var status = "Idle"
    var callDuration = 0
    var isConnected = false
    var isSpeaking = false
    var isListening = false
    var transcripts: [(role: String, text: String)] = []
    var showCaptions = false

    let voiceService = VoiceCallService()
    private var timer: Timer?
    private var audioEngine: AVAudioEngine?
    private var isRecording = false

    func startCall(agentId: String, conversationId: String? = nil) {
        guard let token = APIClient.shared.token else { return }
        status = "Ringing..."
        playRingTone()

        DispatchQueue.main.asyncAfter(deadline: .now() + 1.5) {
            self.voiceService.connect(agentId: agentId, token: token, conversationId: conversationId)
            self.voiceService.onResponseDone = { text in
                self.transcripts.append((role: "assistant", text: text))
            }
            self.isConnected = true
            self.status = "Connected"
            self.startTimer()
            self.startRecording()
        }
    }

    func hangUp() {
        voiceService.disconnect()
        stopRecording()
        timer?.invalidate()
        timer = nil
        isConnected = false
        status = "Ended"
        callDuration = 0
    }

    private func startTimer() {
        timer = Timer.scheduledTimer(withTimeInterval: 1, repeats: true) { _ in
            self.callDuration += 1
        }
    }

    var formattedDuration: String {
        let m = callDuration / 60
        let s = callDuration % 60
        return String(format: "%d:%02d", m, s)
    }

    private func playRingTone() {
        // Simple tone via system sound
        AudioServicesPlaySystemSound(1007) // Standard ring
    }

    func startRecording() {
        guard !isRecording else { return }
        audioEngine = AVAudioEngine()
        guard let engine = audioEngine else { return }
        let input = engine.inputNode
        let format = input.outputFormat(forBus: 0)

        input.installTap(onBus: 0, bufferSize: 4096, format: format) { [weak self] buffer, _ in
            guard let self, self.isListening else { return }
            // Convert buffer to Data and send
            let pcm = buffer.floatChannelData?[0]
            let count = Int(buffer.frameLength)
            guard let pcm else { return }
            var int16 = [Int16](repeating: 0, count: count)
            for i in 0..<count {
                int16[i] = Int16(max(-1, min(1, pcm[i])) * Float(Int16.max))
            }
            let data = Data(bytes: int16, count: count * 2)
            let b64 = data.base64EncodedString()
            self.voiceService.sendAudio(base64: b64)
        }

        do {
            try AVAudioSession.sharedInstance().setCategory(.playAndRecord, mode: .voiceChat)
            try AVAudioSession.sharedInstance().setActive(true)
            try engine.start()
            isRecording = true
            isListening = true
            status = "Listening..."
        } catch {
            status = "Mic error"
        }
    }

    func stopRecording() {
        audioEngine?.inputNode.removeTap(onBus: 0)
        audioEngine?.stop()
        audioEngine = nil
        isRecording = false
        isListening = false
    }
}
