# --- Pre-import Chroma telemetry patch ---
try:
    import chromadb.telemetry as _tele

    class _NoTelemetry:
        def __getattr__(self, name):
            return lambda *args, **kwargs: None

    _tele.capture = lambda *args, **kwargs: None
    _tele.telemetry = _NoTelemetry()
    _tele.opentelemetry = _NoTelemetry()

except Exception:
    pass
