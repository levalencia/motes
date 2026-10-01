import SwiftUI

/// Renders markdown content with proper formatting for tables, code blocks, lists, etc.
struct MarkdownView: View {
    let content: String

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            ForEach(Array(parseBlocks().enumerated()), id: \.offset) { _, block in
                switch block {
                case .table(let headers, let rows):
                    TableBlock(headers: headers, rows: rows)
                case .codeBlock(let code, let lang):
                    CodeBlock(code: code, language: lang)
                case .text(let text):
                    Text(LocalizedStringKey(text))
                        .font(.subheadline)
                        .textSelection(.enabled)
                }
            }
        }
    }

    enum Block {
        case text(String)
        case table(headers: [String], rows: [[String]])
        case codeBlock(code: String, language: String)
    }

    func parseBlocks() -> [Block] {
        var blocks: [Block] = []
        var currentText = ""
        let lines = content.components(separatedBy: "\n")
        var i = 0

        while i < lines.count {
            let line = lines[i]

            // Code block
            if line.hasPrefix("```") {
                if !currentText.isEmpty {
                    blocks.append(.text(currentText.trimmingCharacters(in: .whitespacesAndNewlines)))
                    currentText = ""
                }
                let lang = String(line.dropFirst(3)).trimmingCharacters(in: .whitespaces)
                var code = ""
                i += 1
                while i < lines.count && !lines[i].hasPrefix("```") {
                    code += (code.isEmpty ? "" : "\n") + lines[i]
                    i += 1
                }
                blocks.append(.codeBlock(code: code, language: lang))
                i += 1
                continue
            }

            // Table (line with | characters, followed by separator ---)
            if line.contains("|") && i + 1 < lines.count && lines[i + 1].contains("---") {
                if !currentText.isEmpty {
                    blocks.append(.text(currentText.trimmingCharacters(in: .whitespacesAndNewlines)))
                    currentText = ""
                }
                let headers = parseCells(line)
                i += 2 // skip header + separator
                var rows: [[String]] = []
                while i < lines.count && lines[i].contains("|") {
                    rows.append(parseCells(lines[i]))
                    i += 1
                }
                blocks.append(.table(headers: headers, rows: rows))
                continue
            }

            currentText += (currentText.isEmpty ? "" : "\n") + line
            i += 1
        }

        if !currentText.isEmpty {
            blocks.append(.text(currentText.trimmingCharacters(in: .whitespacesAndNewlines)))
        }
        return blocks
    }

    func parseCells(_ line: String) -> [String] {
        line.split(separator: "|", omittingEmptySubsequences: false)
            .map { $0.trimmingCharacters(in: .whitespaces) }
            .filter { !$0.isEmpty }
    }
}

struct TableBlock: View {
    let headers: [String]
    let rows: [[String]]

    var body: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            VStack(alignment: .leading, spacing: 0) {
                // Header
                HStack(spacing: 0) {
                    ForEach(Array(headers.enumerated()), id: \.offset) { _, h in
                        Text(h)
                            .font(.caption.bold())
                            .padding(.horizontal, 10)
                            .padding(.vertical, 6)
                            .frame(minWidth: 80, alignment: .leading)
                    }
                }
                .background(Color.gray.opacity(0.15))

                // Rows
                ForEach(Array(rows.enumerated()), id: \.offset) { rowIdx, row in
                    HStack(spacing: 0) {
                        ForEach(Array(row.enumerated()), id: \.offset) { _, cell in
                            Text(cell)
                                .font(.caption)
                                .padding(.horizontal, 10)
                                .padding(.vertical, 5)
                                .frame(minWidth: 80, alignment: .leading)
                        }
                    }
                    .background(rowIdx % 2 == 0 ? Color.clear : Color.gray.opacity(0.05))
                }
            }
            .clipShape(RoundedRectangle(cornerRadius: 8))
            .overlay(
                RoundedRectangle(cornerRadius: 8)
                    .stroke(Color.gray.opacity(0.2), lineWidth: 1)
            )
        }
    }
}

struct CodeBlock: View {
    let code: String
    let language: String

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            if !language.isEmpty {
                Text(language)
                    .font(.caption2)
                    .foregroundStyle(.secondary)
                    .padding(.horizontal, 10)
                    .padding(.top, 6)
            }
            ScrollView(.horizontal, showsIndicators: false) {
                Text(code)
                    .font(.system(.caption, design: .monospaced))
                    .padding(10)
                    .textSelection(.enabled)
            }
        }
        .background(Color.gray.opacity(0.1))
        .clipShape(RoundedRectangle(cornerRadius: 8))
    }
}
