"""Registry of the GGUF checkpoints Jev runs, pinned by repository revision and file hash."""

from dataclasses import dataclass
from pathlib import Path

MODELS_DIR = Path("models")


@dataclass(frozen=True)
class GgufFile:
    quant: str
    file: str
    sha256: str
    bytes: int


@dataclass(frozen=True)
class ModelSpec:
    name: str  # what `--model` takes
    source: str  # the original checkpoint the GGUF files were converted from
    repo: str  # Hugging Face repository of the GGUF files
    revision: str  # commit of that repository
    license: str
    architecture: str | None  # `general.architecture` of the files, when known
    files: dict[str, GgufFile]  # by quant

    def path(self, quant: str) -> Path:
        return MODELS_DIR / self.repo.split("/")[1] / self.files[quant].file

    def url(self, quant: str) -> str:
        return f"https://huggingface.co/{self.repo}/resolve/{self.revision}/{self.files[quant].file}"


def _spec(name, source, repo, revision, license, architecture, files):
    return ModelSpec(
        name,
        source,
        repo,
        revision,
        license,
        architecture,
        {quant: GgufFile(quant, file, sha256, size) for quant, file, sha256, size in files},
    )


MODELS = {
    spec.name: spec
    for spec in (
        # GGUF conversions published by the model's authors; hashes are the LFS object ids.
        _spec(
            "spark-4b",
            "XHToken/Spark-X2.5-4B",
            "XHToken/Spark-X2.5-4B-GGUF",
            "9826e0be84e6e6e8b9668abc91421109a1df1e2d",
            "apache-2.0",
            "spark2_5",
            [
                (
                    "q8_0",
                    "Spark-X2.5-4B-Q8_0.gguf",
                    "5c2c3c190e4337e1016b8593ca8e26e8b18c972200b107385d4ec61a25d9dea2",
                    4375021152,
                ),
                (
                    "q4_k_m",
                    "Spark-X2.5-4B-Q4_K_M.gguf",
                    "adfcfa19a4ed6a5985da8bf565fe15f8e1a7e131d79bae2d19d48d1c40109428",
                    2600224352,
                ),
                (
                    "bf16",
                    "Spark-X2.5-4B.gguf",
                    "8cecf405a41a4a10f833530910c2e13fde9fb39c325c8afc3c5d10e4181e1a14",
                    8229920352,
                ),
            ],
        ),
        _spec(
            "spark-1.7b",
            "XHToken/Spark-X2.5-1.7B",
            "XHToken/Spark-X2.5-1.7B-GGUF",
            "1f7fa33b1245c14730da39e125714ad3a327901b",
            "apache-2.0",
            "spark2_5",
            [
                (
                    "q8_0",
                    "Spark-X2.5-1.7B-Q8_0.gguf",
                    "cd77c03185a834bb1162a4b7713520be5838058bfc54873645beff470bb24442",
                    1820112704,
                ),
                (
                    "q4_k_m",
                    "Spark-X2.5-1.7B-Q4_K_M.gguf",
                    "902bde2522394954ac17821b3e5fd0df02defbc6944f122253f2580acf0503f4",
                    1107457856,
                ),
            ],
        ),
        # Community conversions (bartowski) of Google's Gemma 4; hashes are the LFS object ids.
        _spec(
            "gemma-4-e4b",
            "google/gemma-4-E4B-it",
            "bartowski/google_gemma-4-E4B-it-GGUF",
            "029e94146666900b08caf49a3b47b413dfa8ec66",
            "apache-2.0",
            None,
            [
                (
                    "q8_0",
                    "google_gemma-4-E4B-it-Q8_0.gguf",
                    "6a6eba0d36a051b5d924211a889c1436717006e7c5d413830c47caa1d46cb598",
                    8031242720,
                ),
                (
                    "q4_k_m",
                    "google_gemma-4-E4B-it-Q4_K_M.gguf",
                    "d35a3aa7a6d47de237fd488bb6f7f3efd62908d828f85a63da0ee93acdbefe9f",
                    5405170144,
                ),
            ],
        ),
        _spec(
            "gemma-4-12b",
            "google/gemma-4-12B-it",
            "bartowski/gemma-4-12B-it-GGUF",
            "2ae7d41be21ca62de00a2d320ee9cec50daa3aa6",
            "apache-2.0",
            None,
            [
                (
                    "q8_0",
                    "gemma-4-12B-it-Q8_0.gguf",
                    "929bd294cbdc59e41450488bea524a174f1c6ddc43f140fdb5905a5fd1e41969",
                    12669647328,
                ),
                (
                    "q4_k_m",
                    "gemma-4-12B-it-Q4_K_M.gguf",
                    "3962624dcd25b947d889dc9ae1bf275b61db6cd4dbe694057f34fffef1671509",
                    7662533088,
                ),
            ],
        ),
        # Community conversions (bartowski) of Qwen3.5 and of two other Chinese labs' models,
        # plus OpenBMB's own conversion of MiniCPM5; hashes are the LFS object ids.
        _spec(
            "qwen3.5-2b",
            "Qwen/Qwen3.5-2B",
            "bartowski/Qwen_Qwen3.5-2B-GGUF",
            "7d26695454df6de5fbcce2e58681e62dae06ce43",
            "apache-2.0",
            None,
            [
                (
                    "q8_0",
                    "Qwen_Qwen3.5-2B-Q8_0.gguf",
                    "be647507ce6cde229b838924d47bfff9763171105563f7f908670dae57c4dbe2",
                    2080140384,
                ),
                (
                    "q4_k_m",
                    "Qwen_Qwen3.5-2B-Q4_K_M.gguf",
                    "57a1085840f497d764a7fc5d346922dbde961efb54cc792ea81d694fd846a1d8",
                    1396198496,
                ),
            ],
        ),
        _spec(
            "qwen3.5-9b",
            "Qwen/Qwen3.5-9B",
            "bartowski/Qwen_Qwen3.5-9B-GGUF",
            "182be2fd6c7bc44887d88a91cb03ff009cc9f549",
            "apache-2.0",
            None,
            [
                (
                    "q8_0",
                    "Qwen_Qwen3.5-9B-Q8_0.gguf",
                    "b58fe056b5435070240de259f3f981aa38fee96825bbd78c088d5fd90e46f2b5",
                    9804541984,
                ),
                (
                    "q4_k_m",
                    "Qwen_Qwen3.5-9B-Q4_K_M.gguf",
                    "d784ce9eda1a5a7b51e8f705a9e6310844bf4f173654d115823c775fdea56d43",
                    6169341984,
                ),
            ],
        ),
        _spec(
            "minicpm5-2b",
            "openbmb/MiniCPM5-2B",
            "openbmb/MiniCPM5-2B-GGUF",
            "2079a22f3beaa4e306449978533478fe0522f4b3",
            "apache-2.0",
            None,
            [
                (
                    "q8_0",
                    "MiniCPM5-2B-Q8_0.gguf",
                    "c5415f8989bf88a8288f1b55a3cc371af53c07b0faa220a63bd7a990cfaba078",
                    2679710688,
                ),
                (
                    "q4_k_m",
                    "MiniCPM5-2B-Q4_K_M.gguf",
                    "ec2d5801640099e97d8d7e8003ad4d81f336e757811f03a26173dddf386602fd",
                    1561318368,
                ),
            ],
        ),
        _spec(
            "nanbeige4.2-3b",
            "Nanbeige/Nanbeige4.2-3B",
            "bartowski/Nanbeige_Nanbeige4.2-3B-GGUF",
            "17562eefe9752007209148d5f7a6e275fc8d8077",
            "apache-2.0",
            None,
            [
                (
                    "q8_0",
                    "Nanbeige_Nanbeige4.2-3B-Q8_0.gguf",
                    "837ba713ef3a3b5c9aee82e5dcba07600ea7db36ae392419f982b3bfaec04ef2",
                    4434787488,
                ),
                (
                    "q4_k_m",
                    "Nanbeige_Nanbeige4.2-3B-Q4_K_M.gguf",
                    "b92d2e35c9876b0c4bc671996360204f4149d0546c23d5954d5eb3b106c81f24",
                    2684023968,
                ),
            ],
        ),
        _spec(
            "glm-4-9b",
            "THUDM/GLM-4-9B-0414",
            "bartowski/THUDM_GLM-4-9B-0414-GGUF",
            "211924cd949e153b1017ed635e5b127d0b594e6f",
            "mit",
            None,
            [
                (
                    "q8_0",
                    "THUDM_GLM-4-9B-0414-Q8_0.gguf",
                    "7b4ea2795934ca05dc409251dddd289160a194a4d920b575d1de4516808bb50d",
                    9999611264,
                ),
                (
                    "q4_k_m",
                    "THUDM_GLM-4-9B-0414-Q4_K_M.gguf",
                    "2b95f0b88eca423bfb874c4f8e7b9574ec76acab2befd272076e8a8dce31216a",
                    6166574464,
                ),
            ],
        ),
        _spec(
            "qwen3.5-4b",
            "Qwen/Qwen3.5-4B",
            "bartowski/Qwen_Qwen3.5-4B-GGUF",
            "4168f45a16a1290d65a4ec0fa312ae917a4c15d6",
            "apache-2.0",
            None,
            [
                (
                    "q8_0",
                    "Qwen_Qwen3.5-4B-Q8_0.gguf",
                    "5c74c0ede371924357dff0cb6ba145bd67208b9b2389ded681adfff3f7608db7",
                    4622131168,
                ),
                (
                    "q4_k_m",
                    "Qwen_Qwen3.5-4B-Q4_K_M.gguf",
                    "13c16f426047e2de38cd075bdade4a7bcbc8c774384876f677740cda65f8a983",
                    3013027808,
                ),
            ],
        ),
    )
}
# The best model measured on the target GPUs; at q4_k_m it fits 8 GB with the same accuracy.
DEFAULT_MODEL = "glm-4-9b"
DEFAULT_QUANT = "q4_k_m"
QUANTS = ("q8_0", "q4_k_m", "bf16")


def identify(sha256: str) -> tuple[ModelSpec, GgufFile] | None:
    """The pinned registry entry with this file hash, if any."""
    for spec in MODELS.values():
        for file in spec.files.values():
            if file.sha256 == sha256:
                return spec, file
    return None


def download_gguf(model=DEFAULT_MODEL, quant=DEFAULT_QUANT, destination=None, progress=None):
    """Fetch one pinned GGUF file, verified against its sha256."""
    from .runtime.llama_release import fetch

    spec = MODELS[model]
    if quant not in spec.files:
        raise ValueError(f"{model} has no {quant} file; available: {', '.join(spec.files)}")
    target = Path(destination) if destination else spec.path(quant)
    return fetch(spec.url(quant), target, spec.files[quant].sha256, progress)
