import Foundation
import AVFoundation
import UIKit

class AudioPlayerDelegate: NSObject, AVAudioPlayerDelegate {
    var onFinish: (() -> Void)?
    func audioPlayerDidFinishPlaying(_ player: AVAudioPlayer, successfully flag: Bool) {
        onFinish?()
    }
}

@Observable
class CallViewModel {
    var status = "Idle"
    var callDuration = 0
    var isConnected = false
    var isSpeaking = false
    var isListening = false
    var transcripts: [(role: String, text: String)] = []
    var showCaptions = false
    var isSpeaker = true

    let voiceService = VoiceCallService()
    private var timer: Timer?
    private var audioEngine: AVAudioEngine?
    private var isRecording = false
    private let audioDelegate = AudioPlayerDelegate()

    func startCall(agentId: String, conversationId: String? = nil) {
        guard let token = APIClient.shared.token else { return }
        status = "Ringing..."
        playRingTone()

        DispatchQueue.main.asyncAfter(deadline: .now() + 1.5) {
            self.voiceService.onReady = {
                self.isConnected = true
                self.status = "Connected"
                self.startTimer()
                self.startRecording()
            }
            self.voiceService.onAudioReceived = { [weak self] data in
                self?.playAudioData(data)
            }
            self.voiceService.onResponseDone = { text in
                self.transcripts.append((role: "assistant", text: text))
            }
            self.voiceService.onError = { error in
                self.status = "Error: \(error)"
                self.isConnected = false
            }
            self.voiceService.connect(agentId: agentId, token: token, conversationId: conversationId)
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

    private var audioPlayer: AVAudioPlayer?
    private var audioQueue: [Data] = []
    private var isPlayingQueue = false

    private func playAudioData(_ data: Data) {
        audioQueue.append(data)
        if !isPlayingQueue {
            playNextInQueue()
        }
    }

    private func playNextInQueue() {
        guard !audioQueue.isEmpty else {
            isPlayingQueue = false
            return
        }
        isPlayingQueue = true
        let data = audioQueue.removeFirst()
        do {
            audioPlayer = try AVAudioPlayer(data: data)
            audioPlayer?.delegate = audioDelegate
            audioDelegate.onFinish = { [weak self] in
                self?.playNextInQueue()
            }
            audioPlayer?.play()
        } catch {
            print("[Motes] Audio playback error: \(error.localizedDescription)")
            playNextInQueue()
        }
    }

    var formattedDuration: String {
        let m = callDuration / 60
        let s = callDuration % 60
        return String(format: "%d:%02d", m, s)
    }

    private func playRingTone() {
        let generator = UIImpactFeedbackGenerator(style: .medium)
        generator.impactOccurred()
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.4) {
            generator.impactOccurred()
        }
    }

    func toggleSpeaker() {
        isSpeaker.toggle()
        do {
            try AVAudioSession.sharedInstance().overrideOutputAudioPort(isSpeaker ? .speaker : .none)
        } catch { /* ignore */ }
    }

    func startRecording() {
        guard !isRecording else { return }
        audioEngine = AVAudioEngine()
        guard let engine = audioEngine else { return }
        let input = engine.inputNode

        do {
            try AVAudioSession.sharedInstance().setCategory(.playAndRecord, mode: .voiceChat, options: [.defaultToSpeaker, .allowBluetooth])
            try AVAudioSession.sharedInstance().setActive(true)

            // CRITICAL: Enable hardware echo cancellation so agent doesn't hear itself
            try input.setVoiceProcessingEnabled(true)

            let inputFormat = input.outputFormat(forBus: 0)

            // Target format: 24kHz PCM16 Mono — what Azure Realtime API expects
            guard let targetFormat = AVAudioFormat(commonFormat: .pcmFormatInt16,
                                                    sampleRate: 24000,
                                                    channels: 1,
                                                    interleaved: true),
                  let converter = AVAudioConverter(from: inputFormat, to: targetFormat) else {
                status = "Audio format error"
                return
            }

            // Stream directly from tap — no timer, no buffering
            input.installTap(onBus: 0, bufferSize: 2400, format: inputFormat) { [weak self] buffer, _ in
                guard let self, self.isListening else { return }

                let capacity = AVAudioFrameCount(targetFormat.sampleRate / inputFormat.sampleRate * Double(buffer.frameLength))
                guard let targetBuffer = AVAudioPCMBuffer(pcmFormat: targetFormat, frameCapacity: capacity) else { return }

                var error: NSError?
                let inputBlock: AVAudioConverterInputBlock = { _, outStatus in
                    outStatus.pointee = .haveData
                    return buffer
                }

                converter.convert(to: targetBuffer, error: &error, withInputFrom: inputBlock)

                if error == nil, let channelData = targetBuffer.int16ChannelData {
                    let count = Int(targetBuffer.frameLength)
                    let data = Data(bytes: channelData[0], count: count * 2)
                    if data.count > 100 {
                        let b64 = data.base64EncodedString()
                        self.voiceService.sendAudio(base64: b64, sampleRate: 24000)
                    }
                }
            }

            try engine.start()
            isRecording = true
            isListening = true
            status = "Listening..."
        } catch {
            status = "Mic unavailable: \(error.localizedDescription)"
            audioEngine?.inputNode.removeTap(onBus: 0)
            audioEngine = nil
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
