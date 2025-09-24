from datasets import load_dataset
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    TrainingArguments,
    Trainer,
    BitsAndBytesConfig
)
from peft import LoraConfig, get_peft_model
from transformers.trainer_callback import TrainerCallback
import os, glob, torch
from safetensors.torch import load_file as safe_load

# -----------------------------
# Config
# -----------------------------
dataset_path = r"C:/Orion/train/lora_dataset.jsonl"
model_path = r"C:\Orion\lora\~\mistral_models\7B-Instruct-v0.3"
output_dir = "C:/Orion/lora/orion_mystic_lora/live_run"

# -----------------------------
# Load dataset
# -----------------------------
dataset = load_dataset("json", data_files=dataset_path, split="train")

# -----------------------------
# Load tokenizer + patch pad token
# -----------------------------
tokenizer = AutoTokenizer.from_pretrained(model_path)
if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token

# -----------------------------
# Tokenize function
# -----------------------------
def tokenize(batch):
    texts = [p + " " + c for p, c in zip(batch["prompt"], batch["completion"])]
    tokens = tokenizer(
        texts,
        truncation=True,
        padding="max_length",
        max_length=512
    )
    tokens["labels"] = tokens["input_ids"].copy()
    return tokens

tokenized = dataset.map(
    tokenize,
    batched=True,
    remove_columns=dataset.column_names
)

# -----------------------------
# Load model (4-bit quantized for GPU safety)
# -----------------------------
bnb_config = BitsAndBytesConfig(
    load_in_8bit=True,
    llm_int8_threshold=6.0,
    llm_int8_has_fp16_weight=False
)

model = AutoModelForCausalLM.from_pretrained(
    model_path,
    quantization_config=bnb_config,
    device_map="cuda"
)

# -----------------------------
# LoRA Config
# -----------------------------
lora_config = LoraConfig(
    r=8,
    lora_alpha=16,
    lora_dropout=0.05,
    bias="none",
    task_type="CAUSAL_LM"
)

model = get_peft_model(model, lora_config)

# -----------------------------
# Force safetensors-only checkpoints
# -----------------------------
class SafeTensorSaveCallback(TrainerCallback):
    def on_save(self, args, state, control, **kwargs):
        # delete any accidental .bin checkpoints
        for f in glob.glob(os.path.join(args.output_dir, "*.bin")):
            try:
                os.remove(f)
            except OSError:
                pass
        return control

# -----------------------------
# Training Args
# -----------------------------
args = TrainingArguments(
    output_dir=output_dir,
    per_device_train_batch_size=1,
    gradient_accumulation_steps=8,
    learning_rate=2e-4,
    num_train_epochs=3,
    save_strategy="epoch",
    save_safetensors=True,        # force safetensors format
    logging_steps=20,
    fp16=True,
    remove_unused_columns=False
)

# -----------------------------
# Trainer
# -----------------------------
trainer = Trainer(
    model=model,
    args=args,
    train_dataset=tokenized
)

# 🔧 Patch to skip broken optimizer restore
def _noop_load_optimizer_and_scheduler(*args, **kwargs):
    print("⚠️ Skipping optimizer/scheduler restore (only resuming model weights)")
    return None

trainer._load_optimizer_and_scheduler = _noop_load_optimizer_and_scheduler

# -----------------------------
# Resume or Fresh Training
# -----------------------------
latest_ckpt = None
if os.path.isdir(output_dir):
    ckpts = sorted(
        [d for d in glob.glob(os.path.join(output_dir, "checkpoint-*")) if os.path.isdir(d)],
        key=os.path.getmtime,
        reverse=True
    )
    if ckpts:
        latest_ckpt = ckpts[0]

if latest_ckpt:
    print(f"🔄 Resuming weights from {latest_ckpt}")

    # Force skip optimizer/scheduler reload
    trainer._load_optimizer_and_scheduler = lambda *a, **k: None

    # Load model weights manually
    safes = [f for f in os.listdir(latest_ckpt) if f.endswith(".safetensors")]
    if safes:
        state_dict = safe_load(os.path.join(latest_ckpt, safes[0]))
    else:
        state_dict = torch.load(
            os.path.join(latest_ckpt, "pytorch_model.bin"), map_location="cuda"
        )
    model.load_state_dict(state_dict, strict=False)

    # Resume training with fresh optimizer but restored weights
    trainer.train()
else:
    print("🚀 Starting fresh training run")
    trainer.train()

# Final save
final_dir = "C:/Orion/lora/orion_mystic_lora/final"
model.save_pretrained(final_dir, safe_serialization=True)
tokenizer.save_pretrained(final_dir)