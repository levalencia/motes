import Foundation
import Speech
import AVFoundation

@Observable
class SpeechRecognizerService {
    var transcript = ""
    var isListening = false
    var error: String?

    private var audioEngine: AVAudioEngine?
    private var recognitionTask: SFSpeechRecognitionTask?
    private var recognitionRequest: SFSpeechAudioBufferRecognitionRequest?

    func startListening() {
        guard !isListening else { return }

        SFSpeechRecognizer.requestAuthorization { [weak self] status in
            guard status == .authorized else {
                DispatchQueue.main.async { self?.error = "Speech recognition not authorized" }
                return
            }
            DispatchQueue.main.async { self?.beginRecording() }
        }
    }

    private func beginRecording() {
        // Clean up previous session
        stopListening()

        guard let recognizer = SFSpeechRecognizer(), recognizer.isAvailable else {
            error = "Speech recognition unavailable"
            return
        }

        audioEngine = AVAudioEngine()
        guard let engine = audioEngine else { return }
        recognitionRequest = SFSpeechAudioBufferRecognitionRequest()

        guard let request = recognitionRequest else { return }
        request.shouldReportPartialResults = true

        do {
            try AVAudioSession.sharedInstance().setCategory(.record, mode: .measurement)
            try AVAudioSession.sharedInstance().setActive(true)

            let input = engine.inputNode
            let format = input.outputFormat(forBus: 0)

            input.installTap(onBus: 0, bufferSize: 1024, format: format) { buffer, _ in
                request.append(buffer)
            }

            try engine.start()
            isListening = true
            transcript = ""

            recognitionTask = recognizer.recognitionTask(with: request) { [weak self] result, error in
                guard let self else { return }
                if let result {
                    DispatchQueue.main.async {
                        self.transcript = result.bestTranscription.formattedString
                    }
                }
                if error != nil || (result?.isFinal ?? false) {
                    DispatchQueue.main.async {
                        self.stopListening()
                    }
                }
            }
        } catch {
            self.error = "Could not start recording: \(error.localizedDescription)"
            stopListening()
        }
    }

    func stopListening() {
        audioEngine?.inputNode.removeTap(onBus: 0)
        audioEngine?.stop()
        audioEngine = nil
        recognitionRequest?.endAudio()
        recognitionRequest = nil
        recognitionTask?.cancel()
        recognitionTask = nil
        isListening = false
    }
}
