import Foundation

struct Approval: Codable, Identifiable {
    let id: String
    let tool_name: String
    let arguments_json: String
    var status: String // "pending", "approved", "denied"
    let created_at: String?

    var isPending: Bool { status == "pending" }

    var displayName: String {
        let descriptions: [String: String] = [
            "gmail_send": "📧 Send an email via Gmail",
            "outlook_send_email": "📧 Send an email via Outlook",
            "calendar_create": "📅 Create a calendar event",
            "reminders_create": "🔔 Create a reminder in Apple Reminders",
            "file_download_url": "📁 Generate a file download link",
            "pptx_add_slide": "📊 Add a slide to a PowerPoint",
        ]
        return descriptions[tool_name] ?? tool_name.replacingOccurrences(of: "_", with: " ")
    }

    var displayArgs: String {
        guard let data = arguments_json.data(using: .utf8),
              let args = try? JSONSerialization.jsonObject(with: data) as? [String: Any] else {
            return arguments_json
        }
        switch tool_name {
        case "gmail_send", "outlook_send_email":
            let to = args["to"] as? String ?? "?"
            let subject = args["subject"] as? String ?? "?"
            return "To: \(to)\nSubject: \(subject)"
        case "calendar_create":
            let title = args["title"] as? String ?? args["summary"] as? String ?? "?"
            return "Event: \(title)"
        case "reminders_create":
            let title = args["title"] as? String ?? args["text"] as? String ?? args["name"] as? String ?? "?"
            return "Reminder: \(title)"
        default:
            return args.map { "\($0.key): \($0.value)" }.joined(separator: "\n")
        }
    }
}

struct ResolveBody: Codable {
    let approved: Bool
}
