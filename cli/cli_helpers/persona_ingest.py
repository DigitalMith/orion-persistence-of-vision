from .persona_seeder import cmd_persona_load as _cmd_persona_load

def cmd_persona_ingest(args):
    return _cmd_persona_load(args)
