# Recognizer Input Memory Contract v0

Status: binding framework-independent input-adapter safety contract.

Read together with `IMAGE_RESOLUTION_CONTRACT_V0.md` and
`CTC_TEXT_ORDER_V0.md`. This contract bounds the dominant float32 image
allocations created while preparing a recognizer batch. It does not define the
future Android memory implementation.

## 1. Per-line resized width

The recognizer height remains 64 pixels and aspect ratio remains unchanged. The
largest accepted resized width is derived from the existing high-detail page
ceiling and minimum accepted printed-text band height:

```text
ceil(4096 page pixels × 64 recognizer pixels / 24 text-band pixels)
= 10,923 pixels
```

A line whose rounded aspect-preserving width exceeds `10_923` is rejected before
`Image.resize` runs. The existing decoded-source ceiling of 4,000,000 pixels
remains independent and is still enforced.

## 2. Batch working allocation

Before any line is resized, the adapter preflights every image header, grayscale
mode, declared dimensions, optional SHA-256, and resulting width. It then computes:

```text
adapted float32 bytes
  = sum(line_width × 64 × 4)

padded batch float32 bytes
  = batch_size × max_line_width × 64 × 4

working bytes
  = adapted float32 bytes + padded batch float32 bytes
```

`working bytes` must not exceed `256 MiB` (`268,435,456` bytes). Equality is
accepted; one byte above the ceiling is rejected before line resize and before
`np.zeros` allocates the padded tensor.

The budget deliberately counts both temporary resized line arrays and the final
padded batch because both coexist during assembly. Compressed source-file bytes,
small metadata arrays, and CTC target arrays are not part of this dominant image
budget.

## 3. Two-pass safety

1. Preflight reads and validates each source without resizing it.
2. The complete width and working-byte budget is checked.
3. Only an accepted batch enters the resize pass.
4. Each source is revalidated during resize; a changed width fails closed.
5. `np.zeros` is called only after all resized lines match the preflight plan.

Normal accepted batches retain the existing output contract:
`[B, 1, 64, max_width]` float32 pixels, zero/white right padding, exact unpadded
widths, logical text metadata, and alignment-order CTC targets.

## 4. Scope boundary

The 256 MiB value is an offline-reference safety ceiling, not an Android memory
budget and not a recommended training batch size. The mobile implementation must
set a smaller platform-tested budget or stream recognition without silently
raising this contract. This component does not add a neural model, training loop,
weights, predictions, APK, dataset ingestion, privacy processing, or legal analysis.
