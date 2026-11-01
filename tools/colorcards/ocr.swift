// OCR zdjęć kolorników przez macOS Vision. Wynik: JSON [{text, x, y, w, h}] w pikselach (początek u góry z lewej).
import Foundation
import Vision
import AppKit

let path = CommandLine.arguments[1]
guard let img = NSImage(contentsOfFile: path),
      let cg = img.cgImage(forProposedRect: nil, context: nil, hints: nil) else { exit(1) }
let W = Double(cg.width), H = Double(cg.height)
let req = VNRecognizeTextRequest()
req.recognitionLevel = .accurate
req.usesLanguageCorrection = false
try VNImageRequestHandler(cgImage: cg, options: [:]).perform([req])
var out: [[String: Any]] = []
for o in req.results ?? [] {
  guard let c = o.topCandidates(1).first else { continue }
  let b = o.boundingBox
  out.append(["text": c.string, "x": Int(b.minX * W), "y": Int((1 - b.maxY) * H),
              "w": Int(b.width * W), "h": Int(b.height * H)])
}
print(String(data: try JSONSerialization.data(withJSONObject: ["w": Int(W), "h": Int(H), "items": out]), encoding: .utf8)!)
