import platform
import shutil
from pathlib import Path

def _torch_info():
    try:
        import torch
        return {
            "installed": True,
            "version": torch.__version__,
            "cuda_available": torch.cuda.is_available(),
            "gpu_name": (torch.cuda.get_device_name(0) if torch.cuda.is_available() else "N/A"),
        }
    except Exception:
        return {"installed": False, "version": "N/A", "cuda_available": False, "gpu_name": "N/A"}

def _llamacpp_info():
    try:
        from llama_cpp import llama_cpp
        return {"installed": True, "backend": str(llama_cpp.llama_cpp_version())}
    except Exception:
        return {"installed": False, "backend": "N/A"}

def _chroma_info(persist_dir: Path):
    try:
        import chromadb  # noqa
        ok = persist_dir.exists()
        return {"installed": True, "persist_dir_exists": ok}
    except Exception:
        return {"installed": False, "persist_dir_exists": False}

def run(model_path: str, chars_dir: str, chroma_dir: str):
    model = Path(model_path)
    chars = Path(chars_dir)
    chroma = Path(chroma_dir)

    torch_i = _torch_info()
    llama_i = _llamacpp_info()
    chroma_i = _chroma_info(chroma)

    print("=== ORION HEALTH REPORT ===")
    print(f"OS: {platform.system()} {platform.release()}  Python: {platform.python_version()}")
    print(f"Git: {'found' if shutil.which('git') else 'not found'}")
    print()
    print(f"Model file: {'OK' if model.exists() else 'MISSING'} -> {model}")
    print(f"Characters dir: {'OK' if chars.exists() else 'MISSING'} -> {chars}")
    print(f"Chroma persist dir: {'OK' if chroma.exists() else 'MISSING'} -> {chroma}")
    print()
    print(f"Torch: {'installed' if torch_i['installed'] else 'missing'}  "
          f"v={torch_i['version']}  CUDA={torch_i['cuda_available']}  GPU={torch_i['gpu_name']}")
    print(f"llama.cpp (python): {'installed' if llama_i['installed'] else 'missing'} "
          f"backend={llama_i['backend']}")
    print(f"ChromaDB: {'installed' if chroma_i['installed'] else 'missing'}  "
          f"persist_dir_exists={chroma_i['persist_dir_exists']}")
    print("===========================")
