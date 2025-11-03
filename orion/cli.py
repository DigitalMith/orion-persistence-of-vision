"""Command-line interface for Orion."""

import click
import sys
from pathlib import Path
from typing import Optional

from orion.core.assistant import OrionAssistant
from orion.core.config import ConfigLoader


@click.group()
@click.version_option(version="0.1.0")
def main():
    """Orion - Local AI Assistant with Persistent Memory."""
    pass


@main.command()
@click.option('--config', '-c', type=click.Path(exists=True), 
              help='Path to configuration file')
@click.option('--interactive/--no-interactive', '-i/-n', default=True,
              help='Interactive chat mode')
@click.option('--prompt', '-p', type=str,
              help='Single prompt to process (non-interactive mode)')
@click.option('--no-memory', is_flag=True,
              help='Disable memory retrieval')
def chat(config: Optional[str], interactive: bool, prompt: Optional[str], no_memory: bool):
    """Start a chat session with Orion."""
    try:
        assistant = OrionAssistant(config)
        
        if interactive:
            _interactive_chat(assistant, not no_memory)
        elif prompt:
            response = assistant.generate_with_context(
                prompt, 
                use_memory=not no_memory
            )
            click.echo(response)
        else:
            click.echo("Error: Please use --interactive or provide --prompt", err=True)
            sys.exit(1)
    
    except FileNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        click.echo("\nPlease create a configuration file. See 'orion init-config'", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


def _interactive_chat(assistant: OrionAssistant, use_memory: bool):
    """Run interactive chat loop."""
    click.echo("=== Orion Interactive Chat ===")
    click.echo("Type 'quit' or 'exit' to end the session")
    click.echo("Type 'clear' to clear memory")
    click.echo("Type 'stats' to see memory statistics")
    click.echo()
    
    conversation_history = []
    
    while True:
        try:
            user_input = click.prompt("You", type=str, prompt_suffix="> ")
            
            if user_input.lower() in ['quit', 'exit']:
                click.echo("Goodbye!")
                break
            
            if user_input.lower() == 'clear':
                assistant.clear_memory()
                click.echo("Memory cleared.")
                continue
            
            if user_input.lower() == 'stats':
                count = assistant.get_memory_count()
                click.echo(f"Total memories: {count}")
                continue
            
            # Generate response
            response = assistant.chat(
                user_input,
                conversation_history=conversation_history,
                use_memory=use_memory,
                save_to_memory=True
            )
            
            click.echo(f"Orion> {response}")
            click.echo()
            
            # Update conversation history (keep last 10 turns)
            conversation_history.append({'role': 'user', 'content': user_input})
            conversation_history.append({'role': 'assistant', 'content': response})
            
            if len(conversation_history) > 20:
                conversation_history = conversation_history[-20:]
        
        except (KeyboardInterrupt, EOFError):
            click.echo("\nGoodbye!")
            break
        except Exception as e:
            click.echo(f"Error: {e}", err=True)


@main.command()
@click.argument('text')
@click.option('--config', '-c', type=click.Path(exists=True),
              help='Path to configuration file')
@click.option('--emotion', '-e', type=float,
              help='Emotion weight (0.0 to 1.0)')
@click.option('--metadata', '-m', type=str, multiple=True,
              help='Metadata in key=value format')
def add_memory(text: str, config: Optional[str], emotion: Optional[float], metadata: tuple):
    """Add a memory to the database."""
    try:
        assistant = OrionAssistant(config)
        
        # Parse metadata
        meta = {}
        for item in metadata:
            if '=' in item:
                key, value = item.split('=', 1)
                meta[key] = value
        
        memory_id = assistant.add_memory(text, meta if meta else None, emotion)
        click.echo(f"Memory added with ID: {memory_id}")
    
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@main.command()
@click.argument('query')
@click.option('--config', '-c', type=click.Path(exists=True),
              help='Path to configuration file')
@click.option('--n-results', '-n', type=int, default=5,
              help='Number of results to return')
@click.option('--emotion-boost', is_flag=True,
              help='Boost results by emotion weight')
def query(query: str, config: Optional[str], n_results: int, emotion_boost: bool):
    """Query memories similar to the given text."""
    try:
        assistant = OrionAssistant(config)
        results = assistant.query_memory(query, n_results, emotion_boost)
        
        if not results['ids'] or not results['ids'][0]:
            click.echo("No results found.")
            return
        
        click.echo(f"Found {len(results['ids'][0])} results:\n")
        
        for i, doc in enumerate(results['documents'][0]):
            metadata = results['metadatas'][0][i]
            distance = results['distances'][0][i]
            
            click.echo(f"{i+1}. {doc}")
            click.echo(f"   Distance: {distance:.4f}")
            
            if 'emotion' in metadata:
                click.echo(f"   Emotion: {metadata['emotion']:.2f}")
            
            click.echo()
    
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@main.command()
@click.option('--config', '-c', type=click.Path(exists=True),
              help='Path to configuration file')
def stats(config: Optional[str]):
    """Show memory statistics."""
    try:
        assistant = OrionAssistant(config)
        count = assistant.get_memory_count()
        
        click.echo(f"Total memories: {count}")
    
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@main.command()
@click.option('--output', '-o', type=click.Path(),
              default='config/orion.yaml',
              help='Output path for config file')
def init_config(output: str):
    """Initialize a default configuration file."""
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    default_config = {
        'embedding': {
            'model': 'intfloat/e5-large-v2'
        },
        'memory': {
            'database': './chroma_data',
            'collection': 'orion_memory'
        },
        'retrieval': {
            'n_results': 5,
            'emotion_boost': False,
            'context_template': 'Relevant memories:\n{memories}\n\n'
        },
        'llm': {
            'url': 'http://localhost:5000',
            'api_key': None
        }
    }
    
    config = ConfigLoader.__new__(ConfigLoader)
    config.config = default_config
    config.config_path = output_path
    config.save()
    
    click.echo(f"Configuration file created at: {output}")


if __name__ == '__main__':
    main()
