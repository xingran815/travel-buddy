import Foundation

/// Minimal Server-Sent Events client using URLSession data task with delegate.
final class SSEClient: NSObject, URLSessionDataDelegate {

    private var task: URLSessionDataTask?
    private var session: URLSession!
    private var buffer = ""

    var onEvent: ((String) -> Void)?
    var onComplete: (() -> Void)?
    var onError: ((Error) -> Void)?

    override init() {
        super.init()
        session = URLSession(configuration: .default, delegate: self, delegateQueue: nil)
    }

    func start(request: URLRequest) {
        task = session.dataTask(with: request)
        task?.resume()
    }

    func cancel() {
        task?.cancel()
    }

    // MARK: URLSessionDataDelegate

    func urlSession(_ session: URLSession, dataTask: URLSessionDataTask,
                    didReceive data: Data) {
        guard let text = String(data: data, encoding: .utf8) else { return }
        buffer += text
        processBuffer()
    }

    func urlSession(_ session: URLSession, task: URLSessionTask,
                    didCompleteWithError error: Error?) {
        if let error {
            DispatchQueue.main.async { self.onError?(error) }
        } else {
            DispatchQueue.main.async { self.onComplete?() }
        }
    }

    private func processBuffer() {
        // SSE messages are separated by a blank line.
        // sse-starlette uses CRLF; we also accept LF-only servers.
        while let range = nextSeparator() {
            let chunk = String(buffer[buffer.startIndex..<range.lowerBound])
            buffer.removeSubrange(buffer.startIndex..<range.upperBound)
            // Lines inside a chunk may be CRLF or LF separated.
            let lines = chunk.replacingOccurrences(of: "\r\n", with: "\n")
                .components(separatedBy: "\n")
            for line in lines {
                if line.hasPrefix("data: ") {
                    let payload = String(line.dropFirst(6))
                    DispatchQueue.main.async { self.onEvent?(payload) }
                } else if line.hasPrefix("data:") {
                    // Tolerate "data:foo" (no space)
                    let payload = String(line.dropFirst(5))
                    DispatchQueue.main.async { self.onEvent?(payload) }
                }
            }
        }
    }

    private func nextSeparator() -> Range<String.Index>? {
        if let r = buffer.range(of: "\r\n\r\n") { return r }
        if let r = buffer.range(of: "\n\n")     { return r }
        return nil
    }
}
