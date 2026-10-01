import SwiftUI

struct MascotView: View {
    var size: CGFloat = 120
    @State private var floating = false

    var body: some View {
        Image("mascot")
            .resizable()
            .aspectRatio(contentMode: .fit)
            .frame(width: size, height: size)
            .offset(y: floating ? -8 : 0)
            .animation(.easeInOut(duration: 2).repeatForever(autoreverses: true), value: floating)
            .onAppear { floating = true }
    }
}
