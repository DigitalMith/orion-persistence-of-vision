"""Basic usage example for Orion."""

from orion.core.assistant import OrionAssistant

# Initialize Orion with default config
assistant = OrionAssistant()

# Add some memories
print("Adding memories...")
assistant.add_memory(
    "User prefers Python for scripting tasks",
    emotion=0.3
)
assistant.add_memory(
    "User is working on a machine learning project",
    emotion=0.6
)
assistant.add_memory(
    "User's favorite framework is PyTorch",
    emotion=0.8
)

# Add multiple memories at once (pooled memory storage)
assistant.add_memories(
    texts=[
        "User likes to work late at night",
        "User has experience with web development",
        "User is interested in AI research"
    ],
    emotions=[0.4, 0.5, 0.9]
)

print(f"Total memories: {assistant.get_memory_count()}")

# Query memories
print("\nQuerying for 'programming languages'...")
results = assistant.query_memory(
    "programming languages",
    n_results=3,
    emotion_boost=True
)

for i, doc in enumerate(results['documents'][0]):
    print(f"{i+1}. {doc}")

# Generate response with context (requires text-generation-webui running)
# prompt = "What programming language should I use?"
# response = assistant.generate_with_context(prompt)
# print(f"\nResponse: {response}")
