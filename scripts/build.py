"""Build `jev` and put it in a folder that runs anywhere: the binary beside the OpenVINO libraries it loads.

    python scripts/build.py [--build-dir build] [--out dist/jev]

Needs CMake (3.24+), Ninja, a C++17 compiler (on Windows, run from a Visual Studio developer prompt) and
this Python with requirements.txt installed: OpenVINO's C++ SDK and runtime come from its wheel. llama.cpp
(the tokenizer) is fetched and built by CMake. The folder gets `jev`, OpenVINO's core, CPU plugin, IR reader
and TBB, and the licenses (LICENSE, THIRD_PARTY_NOTICES.md, licenses/); put the model folder in it as
`model/` (or pass --model-dir).
"""

import argparse
import importlib.metadata
import platform
import shutil
import subprocess
import sys
from pathlib import Path

import openvino

ROOT = Path(__file__).resolve().parent.parent
OV = Path(openvino.__file__).resolve().parent
LIBS = OV / "libs"


def runtime_files():
    """OpenVINO's files `jev` loads on this OS: the core, the CPU plugin, the IR reader, TBB."""
    system = platform.system()
    if system == "Windows":
        patterns = ["openvino.dll", "openvino_*_cpu_plugin.dll", "openvino_ir_frontend.dll", "tbb12.dll", "tbbmalloc.dll", "tbbbind_2_5.dll"]
    elif system == "Darwin":
        patterns = ["libopenvino.*dylib", "libopenvino_*_cpu_plugin.so", "libopenvino_ir_frontend.*dylib", "libtbb.*dylib", "libtbbmalloc.*dylib"]
    else:
        patterns = ["libopenvino.so*", "libopenvino_*_cpu_plugin.so", "libopenvino_ir_frontend.so*", "libtbb.so*", "libtbbmalloc.so*", "libtbbbind_2_5.so*"]
    files = []
    for pattern in patterns:
        found = sorted(LIBS.glob(pattern))
        if not found and "tbbbind" not in pattern:  # tbbbind (NUMA/hybrid binding) is not shipped everywhere
            sys.exit(f"{LIBS}: nothing matches {pattern}")
        files += found
    return files


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--build-dir", type=Path, default=ROOT / "build")
    ap.add_argument("--out", type=Path, default=ROOT / "dist" / "jev")
    args = ap.parse_args()
    subprocess.run(["cmake", "-S", str(ROOT), "-B", str(args.build_dir), "-G", "Ninja", "-DCMAKE_BUILD_TYPE=Release",
                    f"-DOpenVINO_DIR={OV / 'cmake'}"], check=True)
    subprocess.run(["cmake", "--build", str(args.build_dir)], check=True)
    exe = "jev.exe" if platform.system() == "Windows" else "jev"
    args.out.mkdir(parents=True, exist_ok=True)
    shutil.copy2(args.build_dir / exe, args.out / exe)
    for f in runtime_files():
        # symlinked sonames (libopenvino.so.2640 -> ...) are copied as the files they point to
        shutil.copy2(f, args.out / f.name, follow_symlinks=True)
    licenses = args.out / "licenses"
    for f in importlib.metadata.distribution("openvino").files:  # OpenVINO's, and the third-party programs it ships
        parts = Path(f).parts
        if len(parts) > 2 and parts[0].endswith(".dist-info") and parts[1] == "licenses":
            (licenses / "openvino" / Path(*parts[2:])).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f.locate(), licenses / "openvino" / Path(*parts[2:]))
    (licenses / "llama.cpp").mkdir(parents=True, exist_ok=True)
    shutil.copy2(args.build_dir / "_deps" / "llama_cpp-src" / "LICENSE", licenses / "llama.cpp" / "LICENSE")
    for name in ("LICENSE", "THIRD_PARTY_NOTICES.md"):
        shutil.copy2(ROOT / name, args.out / name)
    print(f"built {args.out / exe} with OpenVINO {openvino.__version__}")


if __name__ == "__main__":
    main()
