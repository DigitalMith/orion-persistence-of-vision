# core/ingest.py

from modules import ingest_logs

def run(args):
    staged = args.staged
    logs = args.logs
    print(f"📥 Starting ingestion from:\n  Staged: {staged}\n  Logs: {logs}")
    ingest_logs.ingest_staged_logs(staged, logs)
    print("✅ Ingestion complete.")
