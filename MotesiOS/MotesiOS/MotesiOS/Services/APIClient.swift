import Foundation

enum SSEEvent {
    case token(String)
    case toolCall(name: String, result: String)
    case done(content: String, conversationId: String?)
    case error(String)
}

@Observable
class APIClient {
    static let shared = APIClient()

    var baseURL: String {
        get { UserDefaults.standard.string(forKey: "motes_server_url") ?? "http://localhost:8001" }
        set { UserDefaults.standard.set(newValue, forKey: "motes_server_url") }
    }

    var token: String? {
        KeychainHelper.readString(key: "motes_token")
    }

    let session = URLSession.shared

    private init() {}

    private func request(_ method: String, path: String, body: Data? = nil) async throws -> (Data, URLResponse) {
        guard let url = URL(string: "\(baseURL)\(path)") else { throw URLError(.badURL) }
        var req = URLRequest(url: url)
        req.httpMethod = method
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        if let t = token { req.setValue("Bearer \(t)", forHTTPHeaderField: "Authorization") }
        if let b = body { req.httpBody = b }
        return try await session.data(for: req)
    }

    func get<T: Decodable>(_ path: String) async throws -> T {
        let (data, resp) = try await request("GET", path: path)
        guard let http = resp as? HTTPURLResponse, http.statusCode == 200 else {
            throw URLError(.badServerResponse)
        }
        return try JSONDecoder().decode(T.self, from: data)
    }

    func post<T: Decodable>(_ path: String, body: some Encodable) async throws -> T {
        let bodyData = try JSONEncoder().encode(body)
        let (data, resp) = try await request("POST", path: path, body: bodyData)
        guard let http = resp as? HTTPURLResponse, http.statusCode < 300 else {
            throw URLError(.badServerResponse)
        }
        return try JSONDecoder().decode(T.self, from: data)
    }

    func delete(_ path: String) async throws {
        let (_, resp) = try await request("DELETE", path: path)
        guard let http = resp as? HTTPURLResponse, http.statusCode < 300 else {
            throw URLError(.badServerResponse)
        }
    }

    func upload(_ path: String, imageData: Data, filename: String) async throws -> [String: Any] {
        guard let url = URL(string: "\(baseURL)\(path)") else { throw URLError(.badURL) }
        var req = URLRequest(url: url)
        req.httpMethod = "POST"
        if let t = token { req.setValue("Bearer \(t)", forHTTPHeaderField: "Authorization") }

        let boundary = UUID().uuidString
        req.setValue("multipart/form-data; boundary=\(boundary)", forHTTPHeaderField: "Content-Type")

        var body = Data()
        body.append("--\(boundary)\r\n".data(using: .utf8)!)
        body.append("Content-Disposition: form-data; name=\"file\"; filename=\"\(filename)\"\r\n".data(using: .utf8)!)
        body.append("Content-Type: image/jpeg\r\n\r\n".data(using: .utf8)!)
        body.append(imageData)
        body.append("\r\n--\(boundary)--\r\n".data(using: .utf8)!)
        req.httpBody = body

        let (data, resp) = try await session.data(for: req)
        guard let http = resp as? HTTPURLResponse, http.statusCode < 300 else {
            throw URLError(.badServerResponse)
        }
        guard let json = try JSONSerialization.jsonObject(with: data) as? [String: Any] else {
            throw URLError(.cannotParseResponse)
        }
        return json
    }

    func streamSSE(path: String, body: some Encodable) -> AsyncStream<SSEEvent> {
        AsyncStream { continuation in
            Task {
                do {
                    guard let url = URL(string: "\(baseURL)\(path)") else { return }
                    var req = URLRequest(url: url)
                    req.httpMethod = "POST"
                    req.setValue("application/json", forHTTPHeaderField: "Content-Type")
                    if let t = token { req.setValue("Bearer \(t)", forHTTPHeaderField: "Authorization") }
                    req.httpBody = try JSONEncoder().encode(body)

                    let (bytes, _) = try await APIClient.shared.session.bytes(for: req)
                    for try await line in bytes.lines {
                        guard line.hasPrefix("data: ") else { continue }
                        let json = String(line.dropFirst(6))
                        guard let data = json.data(using: .utf8),
                              let obj = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
                              let type = obj["type"] as? String else { continue }

                        switch type {
                        case "token":
                            if let c = obj["content"] as? String { continuation.yield(.token(c)) }
                        case "tool_call":
                            let name = obj["tool"] as? String ?? ""
                            let result = obj["result"] as? String ?? ""
                            continuation.yield(.toolCall(name: name, result: result))
                        case "done":
                            let content = obj["content"] as? String ?? ""
                            let convId = obj["conversation_id"] as? String
                            continuation.yield(.done(content: content, conversationId: convId))
                        case "error":
                            let msg = obj["detail"] as? String ?? "Unknown error"
                            continuation.yield(.error(msg))
                        default: break
                        }
                    }
                } catch {
                    continuation.yield(.error(error.localizedDescription))
                }
                continuation.finish()
            }
        }
    }
}

/// Trusts self-signed certificates for local/Tailscale HTTPS
class SelfSignedCertDelegate: NSObject, URLSessionDelegate {
    func urlSession(
        _ session: URLSession,
        didReceive challenge: URLAuthenticationChallenge,
        completionHandler: @escaping (URLSession.AuthChallengeDisposition, URLCredential?) -> Void
    ) {
        if challenge.protectionSpace.authenticationMethod == NSURLAuthenticationMethodServerTrust,
           let trust = challenge.protectionSpace.serverTrust {
            completionHandler(.useCredential, URLCredential(trust: trust))
        } else {
            completionHandler(.performDefaultHandling, nil)
        }
    }
}
