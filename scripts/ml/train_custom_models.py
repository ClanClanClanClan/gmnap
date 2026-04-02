#!/usr/bin/env python3
"""Train surname_only and full_name fastText classifiers."""

import warnings

warnings.filterwarnings("ignore")
import fasttext
from pathlib import Path


def train_model(name, input_file, val_file, word_ngrams, dim):
    print(f"\n=== Training {name} ===")
    model = fasttext.train_supervised(
        input=str(input_file),
        epoch=50,
        lr=0.5,
        wordNgrams=word_ngrams,
        minn=2,
        maxn=5,  # Expert: character n-grams
        dim=dim,
        loss="softmax",
    )

    result = model.test(str(val_file))
    print(
        f"  Val: samples={result[0]}, precision={result[1]:.3f}, recall={result[2]:.3f}"
    )

    out = Path("data/ml_training")

    # Save full
    full_path = out / f"{name}.bin"
    model.save_model(str(full_path))
    print(f"  Full model: {full_path.stat().st_size // 1024} KB")

    # Quantize
    model.quantize(input=str(input_file), retrain=True)
    ftz_path = out / f"{name}.ftz"
    model.save_model(str(ftz_path))
    print(f"  Quantized:  {ftz_path.stat().st_size // 1024} KB")

    return model


base = Path("data/ml_training")

surname_model = train_model(
    "surname_classifier",
    base / "surname_train.txt",
    base / "surname_val.txt",
    word_ngrams=1,
    dim=50,
)

fullname_model = train_model(
    "fullname_classifier",
    base / "fullname_train.txt",
    base / "fullname_val.txt",
    word_ngrams=2,
    dim=100,
)

# Test on some examples
print("\n=== Quick test ===")
for name in [
    "euler",
    "smith",
    "ivanov",
    "tanaka",
    "kim",
    "garcia",
    "müller",
    "papadopoulos",
]:
    s_pred = surname_model.predict(name, k=3)
    print(
        f"  {name:20s} -> {', '.join(f'{l.replace('__label__','')}: {p:.2f}' for l,p in zip(s_pred[0], s_pred[1]))}"
    )
