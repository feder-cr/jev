# Third-party software

`jev` is MIT-licensed (see `LICENSE`). It is built with, and its release archives ship, the software below.
Each archive carries these licenses under `licenses/`.

| Component | Version | License | How `jev` uses it |
|---|---|---|---|
| [OpenVINO](https://github.com/openvinotoolkit/openvino) | 2026.4.0 | Apache-2.0 | runs the model; its runtime libraries ship beside the binary (`licenses/openvino/`, with the third-party programs it includes: oneDNN, oneTBB and others) |
| [oneTBB](https://github.com/uxlfoundation/oneTBB) | as shipped by OpenVINO 2026.4.0 | Apache-2.0 | OpenVINO's threading; shipped beside the binary (`licenses/openvino/`) |
| [llama.cpp](https://github.com/ggml-org/llama.cpp) | b11239 | MIT | its tokenizer, compiled in, with a MiniCPM5 pre-tokenizer added (`third_party/llama-minicpm5`); `licenses/llama.cpp/LICENSE` |
| [cpp-httplib](https://github.com/yhirose/cpp-httplib) | 0.58.0 | MIT | the HTTP server, compiled in (`third_party/httplib.h`) |
| [JSON for Modern C++](https://github.com/nlohmann/json) | 3.12.0 | MIT | JSON of `/health` and `model.json`, compiled in (`third_party/json.hpp`) |

## cpp-httplib

    MIT License

    Copyright (c) 2026 Yuji Hirose. All rights reserved.

    Permission is hereby granted, free of charge, to any person obtaining a copy of this software and
    associated documentation files (the "Software"), to deal in the Software without restriction, including
    without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
    copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the
    following conditions:

    The above copyright notice and this permission notice shall be included in all copies or substantial
    portions of the Software.

    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT
    LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO
    EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
    IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE
    USE OR OTHER DEALINGS IN THE SOFTWARE.

## JSON for Modern C++

    MIT License

    Copyright (c) 2013-2025 Niels Lohmann <https://nlohmann.me>

    Permission is hereby granted, free of charge, to any person obtaining a copy of this software and
    associated documentation files (the "Software"), to deal in the Software without restriction, including
    without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
    copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the
    following conditions:

    The above copyright notice and this permission notice shall be included in all copies or substantial
    portions of the Software.

    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT
    LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO
    EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
    IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE
    USE OR OTHER DEALINGS IN THE SOFTWARE.
