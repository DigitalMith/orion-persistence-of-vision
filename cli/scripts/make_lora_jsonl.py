import os, json, argparse

def main(input_dir, output_file):
    records = []
    for root, _, files in os.walk(input_dir):
        for fname in files:
            if not fname.endswith(".txt"):
                continue
            fpath = os.path.join(root, fname)
            with open(fpath, "r", encoding="utf-8") as f:
                text = f.read().strip()
            if not text:
                continue

            # Voice or Study label based on folder
            role = "voice" if "voice" in root.lower() else "study"

            record = {
                "prompt": f"{role.capitalize()} Excerpt:",
                "completion": text
            }
            records.append(record)

    with open(output_file, "w", encoding="utf-8") as out:
        for r in records:
            out.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"✅ {len(records)} records written to {output_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default=r"C:\Orion\train\output")
    parser.add_argument("--output", default=r"C:\Orion\train\lora_dataset.jsonl")
    args = parser.parse_args()
    main(args.input, args.output)
