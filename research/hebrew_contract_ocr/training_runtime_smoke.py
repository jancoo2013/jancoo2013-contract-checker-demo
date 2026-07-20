from __future__ import annotations

import json


def runtime_report() -> dict[str, object]:
    try:
        import torch
        import torch.nn.functional as functional
    except ImportError as exc:
        raise RuntimeError(
            "install research/hebrew_contract_ocr/requirements-training.txt"
        ) from exc

    if torch.version.cuda is not None or torch.cuda.is_available():
        raise RuntimeError("OCR training runtime v0 must use the CPU-only PyTorch build")

    pixels = torch.arange(64, dtype=torch.float32).reshape(1, 1, 8, 8)
    kernel = torch.ones((1, 1, 3, 3), dtype=torch.float32)
    output = functional.conv2d(pixels, kernel)
    if tuple(output.shape) != (1, 1, 6, 6):
        raise RuntimeError(f"unexpected convolution shape: {tuple(output.shape)}")
    if float(output[0, 0, 0, 0]) != 81.0 or not bool(torch.isfinite(output).all()):
        raise RuntimeError("deterministic CPU convolution smoke failed")

    return {
        "torch_version": torch.__version__,
        "cuda_build": torch.version.cuda,
        "device": str(output.device),
        "output_shape": list(output.shape),
        "output_sum": float(output.sum()),
    }


def main() -> None:
    print(json.dumps(runtime_report(), sort_keys=True))


if __name__ == "__main__":
    main()
