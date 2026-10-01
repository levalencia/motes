import SwiftUI

struct LoginView: View {
    @Bindable var vm: AuthViewModel

    var body: some View {
        VStack(spacing: 0) {
            Spacer()

            MascotView(size: 80)
                .padding(.bottom, 8)
            Text("Motes")
                .font(.title.bold())

            VStack(spacing: 16) {
                TextField("Server URL", text: $vm.serverURL)
                    .textFieldStyle(.roundedBorder)
                    .textContentType(.URL)
                    .autocapitalization(.none)
                    .font(.caption)

                TextField("Username", text: $vm.username)
                    .textFieldStyle(.roundedBorder)
                    .textContentType(.username)
                    .autocapitalization(.none)

                SecureField("Password", text: $vm.password)
                    .textFieldStyle(.roundedBorder)
                    .textContentType(.password)

                if let err = vm.error {
                    Text(err)
                        .font(.caption)
                        .foregroundStyle(.red)
                }

                Button {
                    Task { await vm.login() }
                } label: {
                    Text(vm.isLoading ? "Signing in..." : "Sign In")
                        .font(.headline)
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 12)
                        .background(MotesTheme.gradient)
                        .foregroundStyle(.white)
                        .clipShape(RoundedRectangle(cornerRadius: 14))
                }
                .disabled(vm.isLoading || vm.username.isEmpty || vm.password.isEmpty)
            }
            .padding(24)
            .background(Color(uiColor: .secondarySystemBackground))
            .clipShape(RoundedRectangle(cornerRadius: 20))
            .padding(.horizontal, 24)
            .padding(.top, 24)

            Spacer()
        }
    }
}
