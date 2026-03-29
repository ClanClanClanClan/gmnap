from datasets import load_dataset

for name in ["lcw99/cc100-ko-only", "mc4", "aihub_korean_news"]:
    try:
        ds = load_dataset(name, "ko", split="train", cache_dir="data/corp")
        print(name, len(ds))
    except Exception as e:
        print("Skip", name, e)
