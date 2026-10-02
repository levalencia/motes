import SwiftUI

struct ApprovalCardView: View {
    let approval: Approval
    let onApprove: () -> Void
    let onDeny: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack {
                Image(systemName: "shield.checkered")
                    .foregroundStyle(.orange)
                Text("Approval Required")
                    .font(.caption.bold())
                    .foregroundStyle(.orange)
                Spacer()
            }

            Text(approval.description)
                .font(.subheadline)
                .foregroundStyle(.primary)

            if approval.isPending {
                HStack(spacing: 12) {
                    Button {
                        onApprove()
                    } label: {
                        HStack(spacing: 4) {
                            Image(systemName: "checkmark")
                            Text("Approve")
                        }
                        .font(.subheadline.bold())
                        .foregroundStyle(.white)
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 8)
                        .background(Color.green)
                        .clipShape(RoundedRectangle(cornerRadius: 8))
                    }
                    .buttonStyle(.plain)

                    Button {
                        onDeny()
                    } label: {
                        HStack(spacing: 4) {
                            Image(systemName: "xmark")
                            Text("Deny")
                        }
                        .font(.subheadline.bold())
                        .foregroundStyle(.white)
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 8)
                        .background(Color.red)
                        .clipShape(RoundedRectangle(cornerRadius: 8))
                    }
                    .buttonStyle(.plain)
                }
            } else {
                HStack {
                    Spacer()
                    if approval.status == "approved" {
                        Label("Approved ✓", systemImage: "checkmark.circle.fill")
                            .foregroundStyle(.green)
                            .font(.subheadline.bold())
                    } else {
                        Label("Denied ✗", systemImage: "xmark.circle.fill")
                            .foregroundStyle(.red)
                            .font(.subheadline.bold())
                    }
                    Spacer()
                }
            }
        }
        .padding(12)
        .background(Color.orange.opacity(0.08))
        .clipShape(RoundedRectangle(cornerRadius: 14))
        .overlay(
            RoundedRectangle(cornerRadius: 14)
                .stroke(Color.orange.opacity(0.3), lineWidth: 1)
        )
    }
}
