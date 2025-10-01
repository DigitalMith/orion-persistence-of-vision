# core/persona.py

from modules import persona_utils

def check(args):
    print("🧠 Running persona check...")
    persona_utils.run_persona_check()

def seed(args):
    from modules import persona_utils
    persona_utils.seed_persona(args.file)

def recall(args):
    from modules import persona_utils
    persona_utils.recall_persona()

