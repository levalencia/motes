import SwiftUI
import PhotosUI

struct ChatComposer: View {
    @Binding var text: String
    var isStreaming: Bool = false
    var isRecording: Bool = false
    var attachedImage: UIImage? = nil
    var isUploadingImage: Bool = false
    var onSend: () -> Void = {}
    var onMicStart: () -> Void = {}
    var onMicStop: () -> Void = {}
    var onImageSelected: ((UIImage) -> Void)? = nil
    var onRemoveImage: (() -> Void)? = nil

    @State private var showAttachSheet = false
    @State private var showCamera = false
    @State private var selectedPhotoItem: PhotosPickerItem?

    var body: some View {
        VStack(spacing: 0) {
            // Image preview strip
            if let image = attachedImage {
                HStack {
                    Image(uiImage: image)
                        .resizable()
                        .scaledToFill()
                        .frame(width: 60, height: 60)
                        .clipShape(RoundedRectangle(cornerRadius: 8))
                        .overlay(alignment: .topTrailing) {
                            Button {
                                onRemoveImage?()
                            } label: {
                                Image(systemName: "xmark.circle.fill")
                                    .font(.caption)
                                    .foregroundStyle(.white)
                                    .background(Circle().fill(Color.black.opacity(0.6)))
                            }
                            .offset(x: 4, y: -4)
                        }

                    if isUploadingImage {
                        ProgressView()
                            .padding(.leading, 8)
                        Text("Uploading...")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }

                    Spacer()
                }
                .padding(.horizontal, 12)
                .padding(.top, 8)
            }

            HStack(alignment: .bottom, spacing: 8) {
                // Attach button
                Button {
                    showAttachSheet = true
                } label: {
                    Image(systemName: "paperclip")
                        .foregroundStyle(.secondary)
                }
                .confirmationDialog("Attach Image", isPresented: $showAttachSheet) {
                    PhotosPicker(selection: $selectedPhotoItem, matching: .images) {
                        Text("Photo Library")
                    }
                    Button("Take Photo") {
                        showCamera = true
                    }
                    Button("Cancel", role: .cancel) {}
                }

                TextField("Message Motes...", text: $text, axis: .vertical)
                    .lineLimit(1...5)
                    .padding(.horizontal, 12)
                    .padding(.vertical, 10)
                    .font(.subheadline)

                // Mic button — tap to toggle recording
                Button(action: {
                    if isRecording {
                        onMicStop()
                    } else {
                        onMicStart()
                    }
                }) {
                    Image(systemName: isRecording ? "mic.fill" : "mic")
                        .foregroundStyle(isRecording ? MotesTheme.accent : .secondary)
                        .symbolEffect(.pulse, isActive: isRecording)
                }

                Button(action: onSend) {
                    Image(systemName: "arrow.up")
                        .font(.subheadline.bold())
                        .foregroundStyle(.white)
                        .frame(width: 32, height: 32)
                        .background(
                            canSend
                                ? AnyShapeStyle(MotesTheme.gradient)
                                : AnyShapeStyle(Color.gray.opacity(0.3))
                        )
                        .clipShape(Circle())
                }
                .disabled(!canSend || isStreaming)
            }
            .padding(.horizontal, 12)
            .padding(.vertical, 8)
        }
        .background(Color.gray.opacity(0.1))
        .clipShape(RoundedRectangle(cornerRadius: 24))
        .shadow(color: .black.opacity(0.06), radius: 8, y: 2)
        .padding(.horizontal, 12)
        .padding(.bottom, 8)
        .fullScreenCover(isPresented: $showCamera) {
            CameraPickerView(image: Binding(
                get: { nil },
                set: { newImage in
                    if let img = newImage { onImageSelected?(img) }
                }
            ))
            .ignoresSafeArea()
        }
        .onChange(of: selectedPhotoItem) {
            Task {
                if let item = selectedPhotoItem,
                   let data = try? await item.loadTransferable(type: Data.self),
                   let uiImage = UIImage(data: data) {
                    onImageSelected?(uiImage)
                }
                selectedPhotoItem = nil
            }
        }
    }

    private var canSend: Bool {
        !text.trimmingCharacters(in: .whitespaces).isEmpty || attachedImage != nil
    }
}
