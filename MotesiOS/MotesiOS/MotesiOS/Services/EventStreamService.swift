import Foundation

struct ProactiveEvent {
    let title: String
    let body: String
    let category: String
}

@Observable
class EventStreamService {
    var latestEvent: ProactiveEvent?
    private var task: Task<Void, Never>?

    func start() {
        guard let token = APIClient.shared.token else { return }
        let urlStr = "\(APIClient.shared.baseURL)/api/events/stream?token=\(token)"
        guard let url = URL(string: urlStr) else { return }

        task = Task {
            do {
                let (bytes, _) = try await URLSession.shared.bytes(from: url)
                for try await line in bytes.lines {
                    guard !Task.isCancelled else { break }
                    guard line.hasPrefix("data: ") else { continue }
                    let json = String(line.dropFirst(6))
                    guard let data = json.data(using: .utf8),
                          let obj = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
                          let title = obj["title"] as? String,
                          let body = obj["body"] as? String else { continue }
                    let category = obj["category"] as? String ?? "info"
                    await MainActor.run {
                        self.latestEvent = ProactiveEvent(title: title, body: body, category: category)
                    }
                }
            } catch { /* stream ended */ }
        }
    }

    func stop() {
        task?.cancel()
        task = nil
    }
}
