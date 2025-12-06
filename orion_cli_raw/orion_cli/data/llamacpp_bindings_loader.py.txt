# modules/llamacpp_bindings_loader.py
# Minimal llama.cpp Python bindings loader for TGWUI.

import os
from llama_cpp import Llama
from modules import shared
from modules.utils import resolve_model_path

def _cpu_threads():
    try:
        return max(1, (os.cpu_count() or 1) - 1)
    except Exception:
        return 1

def load_llamacpp_bindings(model_name: str):
    """
    Returns (model, tokenizer) to match TGWUI expectations.
    For Llama.cpp bindings, tokenizer is None (handled upstream).
    """
    model_path = resolve_model_path(model_name)

    # Pull common knobs from shared.args if present; otherwise sensible defaults
    args = shared.args
    n_ctx = getattr(args, "ctx_size", 2048)
    n_threads = getattr(args, "threads", _cpu_threads())
    n_gpu_layers = getattr(args, "n_gpu_layers", 0)  # keep 0 for CPU; set >0 if you later use CUDA build
    seed = getattr(args, "seed", 0)

    llm = Llama(
        model_path=str(model_path),
        n_ctx=n_ctx,
        n_threads=n_threads,
        n_gpu_layers=n_gpu_layers,
        seed=seed or 0,
        # You can add more params later as needed:
        # f16_kv=True, logits_all=False, embedding=False, use_mlock=False, etc.
    )

    # Return (model, tokenizer); TGWUI callers tolerate tokenizer=None on llamacpp
    return (llm, None)
