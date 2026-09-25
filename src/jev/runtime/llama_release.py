# Derived from Rizzo Flow — https://github.com/Rizzo-AI-Academy/rizzo-flow
# Copyright 2026 Simone Rizzo — Rizzo AI Academy. Licensed under the Apache License 2.0.
# Modifications for Jev: Copyright 2026 Loris Salsi. See NOTICE.
"""Pinned llama.cpp runtime: official prebuilt packages, verified by sha256, one per platform.

Nothing is compiled. `jev download` fetches the release archive that matches this machine
from github.com/ggml-org/llama.cpp and unpacks it under `runtimes/`. The ctypes layouts in
`llama_cpp.py` are transcribed from the header of exactly this release, so a directory given
through `JEV_LLAMA_DIR` must hold a build of the same commit.
"""

import copy
import ctypes
import hashlib
import http.client
import os
import platform
import shutil
import sys
import tarfile
import urllib.request
import zipfile
from pathlib import Path

RELEASE = "b11081"
COMMIT = "161755f29e415e2c33efe906e91843c068efd664"
BASE_URL = f"https://github.com/ggml-org/llama.cpp/releases/download/{RELEASE}"
RUNTIME_DIR_ENV = "JEV_LLAMA_DIR"
RUNTIMES = Path("runtimes")
# User-facing accelerator families. `vulkan` drives AMD, Intel and NVIDIA GPUs alike; `cuda12`
# is the CUDA 12.8 build for Linux hosts whose driver predates CUDA 13 (cloud pods, older
# datacenter images).
ACCELERATORS = ("auto", "metal", "cuda", "cuda12", "vulkan", "rocm", "sycl", "cpu")
# (os, machine, accelerator) -> archives to unpack into one directory, with their sha256.
PACKAGES = {
    ("darwin", "arm64", "metal"): [
        (
            "llama-b11081-bin-macos-arm64.tar.gz",
            "ee4ffbf0e35224a9e4ac1709120a1b5a0e3376594c8a40fab89bb92bd1621434",
        )
    ],
    ("darwin", "x64", "cpu"): [
        (
            "llama-b11081-bin-macos-x64.tar.gz",
            "b68056a01648554a9b85ff716b56a7fbf6787ddd8d54c1b76a43cf08c66cb486",
        )
    ],
    ("win32", "x64", "cuda"): [
        (
            "llama-b11081-bin-win-cuda-13.4-x64.zip",
            "fefb4d9751d36cbb5b82042729470fddf3a47841aa8c91025cd7de1dc2767e58",
        ),
        (
            "cudart-llama-bin-win-cuda-13.4-x64.zip",
            "738f8c251ac22b70c3ae6f83a10cf222725df0395246a2cf58f32bdb85fbe668",
        ),
    ],
    ("win32", "x64", "vulkan"): [
        (
            "llama-b11081-bin-win-vulkan-x64.zip",
            "4259a1dda3ef3fcfd8b007a16329d5bdcef07da8f5f95fddd85ff2954263f01a",
        )
    ],
    ("win32", "x64", "rocm"): [
        (
            "llama-b11081-bin-win-rocm-10.0-x64.zip",
            "3c6ef7351a0b23f6ff27598893d4c45bb405d508f90bbe0e6a5c7f978c7ba6f8",
        )
    ],
    ("win32", "x64", "sycl"): [
        (
            "llama-b11081-bin-win-sycl-x64.zip",
            "95516fec72d62a57e3976399f7cde5e212704705ccf689a9920aef0bf2cea884",
        )
    ],
    ("win32", "x64", "cpu"): [
        (
            "llama-b11081-bin-win-cpu-x64.zip",
            "48f13c153946cca8543fd3ab915709ec5f340bfe1f38c687121b3d58f848b7b2",
        )
    ],
    ("win32", "arm64", "cpu"): [
        (
            "llama-b11081-bin-win-cpu-arm64.zip",
            "c39f04251c9f92a32e1e936e67a5e77175f469c244ef760305b292b1e6d79a24",
        )
    ],
    ("linux", "x64", "cuda"): [
        (
            "llama-b11081-bin-ubuntu-cuda-13.4-x64.tar.gz",
            "71984fb15c371a34e79b773000a712ea6a7ff228e62b6ee6313a7881897ea931",
        ),
        (
            "cudart-llama-b11081-bin-ubuntu-cuda-13.4-x64.tar.gz",
            "c86d7a48e65d8bda58f79a288599508c8b0e57e711118c30b8e1228faf7dc898",
        ),
    ],
    ("linux", "x64", "cuda12"): [
        (
            "llama-b11081-bin-ubuntu-cuda-12.8-x64.tar.gz",
            "a539df4fb429302e88c1e03248ed46dd7dfe14db19f0c5a4def713dd15a6512b",
        ),
        (
            "cudart-llama-b11081-bin-ubuntu-cuda-12.8-x64.tar.gz",
            "6a3b3f757b81d8a4d68020c27823782db207c468884fbbd716112c8e0b81125d",
        ),
    ],
    ("linux", "arm64", "cuda"): [
        (
            "llama-b11081-bin-ubuntu-cuda-13.4-arm64.tar.gz",
            "5258609c6fd99fc6a4a0ca378915cc11a71983927d78a48fe9e0805d9b832225",
        ),
        (
            "cudart-llama-b11081-bin-ubuntu-cuda-13.4-arm64.tar.gz",
            "ea54932d0a3d30096340c7bf10b8872ea88750c05bf768396bf7ca38ab682fcc",
        ),
    ],
    ("linux", "x64", "vulkan"): [
        (
            "llama-b11081-bin-ubuntu-vulkan-x64.tar.gz",
            "60f576a7b5bc1d0711ad980bb2814ab9885dbe670325842132449e42ab1522b8",
        )
    ],
    ("linux", "arm64", "vulkan"): [
        (
            "llama-b11081-bin-ubuntu-vulkan-arm64.tar.gz",
            "b1dd6892173fffdee635061e73f5c99de025ca21e376fa1b628933f0245887f4",
        )
    ],
    ("linux", "x64", "rocm"): [
        (
            "llama-b11081-bin-ubuntu-rocm-10.0-x64.tar.gz",
            "e54ba1e83fe4564e952a59deec0669e9281f119aa15d06bec5279256a0bb3094",
        )
    ],
    ("linux", "x64", "sycl"): [
        (
            "llama-b11081-bin-ubuntu-sycl-fp16-x64.tar.gz",
            "38afe41c0394b6217ab68263377c436b30b7f1950de03f214879adb7dd42cf77",
        )
    ],
    ("linux", "x64", "cpu"): [
        (
            "llama-b11081-bin-ubuntu-x64.tar.gz",
            "1e4afeb3985ff8877c3811b7fa994faf7731fb54ad90ff0b68e96fb0a5493c45",
        )
    ],
    ("linux", "arm64", "cpu"): [
        (
            "llama-b11081-bin-ubuntu-arm64.tar.gz",
            "bac885ec719971e4e149369a3172b0e5b6275ec53fece4c9050a9948dee03971",
        )
    ],
}
# Order in which an installed runtime is picked when several are present.
PREFERENCE = ("metal", "cuda", "cuda12", "rocm", "sycl", "vulkan", "cpu")
LIBRARY_NAMES = {"win32": "llama.dll", "darwin": "libllama.dylib"}


def host() -> tuple[str, str]:
    """(os, machine) in the vocabulary of `PACKAGES`."""
    system = "linux" if sys.platform.startswith("linux") else sys.platform
    machine = platform.machine().lower()
    return system, {"amd64": "x64", "x86_64": "x64", "aarch64": "arm64"}.get(machine, machine)


def library_name() -> str:
    return LIBRARY_NAMES.get(sys.platform, "libllama.so")


def nvidia_driver() -> bool:
    """An NVIDIA driver is installed: its user-mode library loads. No CUDA toolkit needed."""
    name = "nvcuda.dll" if sys.platform == "win32" else "libcuda.so.1"
    try:
        ctypes.CDLL(name)
    except OSError:
        return False
    return True


def supported(system: str | None = None, machine: str | None = None) -> list[str]:
    here = host()
    key = (system or here[0], machine or here[1])
    return [name for name in PREFERENCE if (*key, name) in PACKAGES]


def pick(accelerator: str = "auto") -> str:
    """Accelerator family to install here. `auto`: Metal, else CUDA with an NVIDIA driver,
    else Vulkan (any GPU vendor; it falls back to the CPU when there is no GPU), else CPU."""
    if accelerator not in ACCELERATORS:
        raise ValueError(f"Runtime must be one of: {', '.join(ACCELERATORS)}")
    available = supported()
    if not available:
        raise ValueError(
            f"No prebuilt llama.cpp {RELEASE} package for {'/'.join(host())}. Build commit "
            f"{COMMIT[:7]} with -DBUILD_SHARED_LIBS=ON and point {RUNTIME_DIR_ENV} at it."
        )
    if accelerator != "auto":
        if accelerator not in available:
            raise ValueError(
                f"No {accelerator} package for {'/'.join(host())}; available: {', '.join(available)}"
            )
        return accelerator
    if "metal" in available:
        return "metal"
    if "cuda" in available and nvidia_driver():
        return "cuda"
    return "vulkan" if "vulkan" in available else available[0]


def install_dir(accelerator: str) -> Path:
    system, machine = host()
    return RUNTIMES / f"llama-{RELEASE}-{system}-{machine}-{accelerator}"


def find_library(directory: Path) -> Path | None:
    """The libllama file of a runtime directory; release tarballs nest it one level down."""
    directory = Path(directory)
    for candidate in (directory, *sorted(p for p in directory.glob("*") if p.is_dir())):
        if (candidate / library_name()).is_file():
            return candidate / library_name()
    return None


def locate(family: str | None = None) -> Path:
    """Directory holding libllama: `JEV_LLAMA_DIR`, else the installed pinned runtime of the
    requested GPU family (`--device vulkan`), else the best one installed."""
    override = os.environ.get(RUNTIME_DIR_ENV)
    if override:
        library = find_library(Path(override))
        if library is None:
            raise ValueError(f"{RUNTIME_DIR_ENV}={override}: {library_name()} not found there")
        return library.parent
    for accelerator in sorted(supported(), key=lambda name: name != family):
        library = find_library(install_dir(accelerator))
        if library is not None:
            return library.parent
    raise ValueError(
        f"llama.cpp runtime not installed. Run `jev download` (runtime + weights) or "
        f"`jev download --only runtime`; or set {RUNTIME_DIR_ENV} to a build of {COMMIT[:7]}."
    )


def installed() -> list[str]:
    return [name for name in supported() if find_library(install_dir(name)) is not None]


def sha256_file(path: Path) -> str:
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def fetch(url: str, target: Path, sha256: str, progress=None, attempts: int = 5) -> Path:
    """Download to `target` unless a verified copy is already there; never keep a bad file.

    Multi-gigabyte transfers get cut: an interrupted download resumes from the bytes already
    on disk (HTTP Range) instead of starting over, and only the sha256 decides success."""
    target = Path(target)
    if target.is_file() and sha256_file(target) == sha256:
        return target
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_name(target.name + ".part")
    failure = None
    for _ in range(attempts):
        have = partial.stat().st_size if partial.exists() else 0
        headers = {"User-Agent": "jev"}
        if have:
            headers["Range"] = f"bytes={have}-"
        try:
            request = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(request, timeout=120) as response:
                resumed = have and getattr(response, "status", 200) == 206
                total = int(response.headers.get("Content-Length") or 0) + (have if resumed else 0)
                done = have if resumed else 0
                with partial.open("ab" if resumed else "wb") as out:
                    while block := response.read(1 << 20):
                        out.write(block)
                        done += len(block)
                        if progress:
                            progress(target.name, done, total)
            if total and done < total:
                failure = f"connection closed at {done} of {total} bytes"
                continue
        except (OSError, http.client.HTTPException) as error:  # resets, timeouts, short reads
            failure = str(error)
            continue
        digest = sha256_file(partial)
        if digest != sha256:
            partial.unlink()
            raise ValueError(f"{target.name}: sha256 mismatch (expected {sha256}, got {digest})")
        partial.replace(target)
        return target
    raise ValueError(f"{target.name}: download failed after {attempts} attempts ({failure})")


def unpack(archive: Path, destination: Path) -> None:
    """Extract a release archive; members that would escape the destination are refused."""
    destination = Path(destination).resolve()
    destination.mkdir(parents=True, exist_ok=True)
    if archive.name.endswith(".zip"):
        with zipfile.ZipFile(archive) as bundle:
            for member in bundle.namelist():
                if not (destination / member).resolve().is_relative_to(destination):
                    raise ValueError(f"{archive.name}: unsafe member {member}")
            bundle.extractall(destination)
    else:
        with tarfile.open(archive) as bundle:
            for member in bundle:
                # Every tarball wraps its files in one folder of its own; drop it, so the
                # runtime and the CUDA libraries shipped separately end up side by side.
                inner = member.name.split("/", 1)[1:]
                if not inner or not inner[0]:
                    continue
                member = copy.copy(member)
                member.name = inner[0]
                # The `data` filter rejects absolute paths, links and devices leaving the tree.
                bundle.extract(member, destination, filter="data")


def install(accelerator: str = "auto", progress=None) -> Path:
    """Download, verify and unpack the pinned runtime for this machine; idempotent."""
    accelerator = pick(accelerator)
    directory = install_dir(accelerator)
    library = find_library(directory)
    if library is not None:
        return library.parent
    staging = directory.with_name(directory.name + ".partial")
    shutil.rmtree(staging, ignore_errors=True)
    for name, sha256 in PACKAGES[(*host(), accelerator)]:
        archive = fetch(f"{BASE_URL}/{name}", RUNTIMES / "downloads" / name, sha256, progress)
        unpack(archive, staging)
    if find_library(staging) is None:
        raise ValueError(f"{library_name()} not found in the {accelerator} package")
    staging.replace(directory)
    return find_library(directory).parent
