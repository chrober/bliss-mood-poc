# bliss-mood-poc

Experimental Rust music mood recognition research for [bliss-rs](https://github.com/Polochon-street/bliss-rs) and Lyrion, following the [similarity design](https://chrober.github.io/bliss-similarity-design/).

**Status:** Initial research / unvalidated implementation. The target is offline mood analysis with Essentia's MTG-Jamendo ONNX models, reproducible validation, and optional integration in the existing Bliss mixer. No model weights are distributed here. The model licenses must be reviewed separately.

The existing Bliss feature vector and Lyrion production plugins remain unchanged during the proof of concept.
