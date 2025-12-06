# Bypass Gradio's "localhost must be reachable" gates so we can launch without --share.
# We patch multiple places because different 4.x builds call different helpers.
def _always_true(*a, **k): return True

# --- gradio.networking (common in 4.x) ---
try:
    import gradio.networking as gn
    for name in ("url_ok", "is_intranet", "is_local_url", "check_localhost", "check_is_localhost"):
        if hasattr(gn, name):
            setattr(gn, name, _always_true)
except Exception:
    pass

# --- gradio.utils (some builds check here) ---
try:
    import gradio.utils as gu
    if hasattr(gu, "url_ok"):
        gu.url_ok = _always_true
    if hasattr(gu, "is_intranet"):
        gu.is_intranet = _always_true
except Exception:
    pass

# --- gradio_client.utils (many 4.x builds import url_ok from here) ---
try:
    import gradio_client.utils as gcu
    if hasattr(gcu, "url_ok"):
        gcu.url_ok = _always_true
except Exception:
    pass

# --- final fallback: class method on Blocks (some builds call this) ---
try:
    from gradio.blocks import Blocks
    if hasattr(Blocks, "_verify_local_url"):
        Blocks._verify_local_url = lambda self: True
except Exception:
    pass

print("[patch] gradio localhost check bypass active")
