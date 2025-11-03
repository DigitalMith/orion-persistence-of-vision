"""Example demonstrating emotion-weighted context retrieval."""

from orion.core.assistant import OrionAssistant

# Initialize assistant
assistant = OrionAssistant()

# Add memories with varying emotion weights
memories = [
    ("User mentioned they enjoy hiking", 0.3),
    ("User was very excited about their new puppy", 0.9),
    ("User casually mentioned they like coffee", 0.2),
    ("User was deeply moved by a book they read", 0.8),
    ("User needs to buy groceries", 0.1),
]

print("Adding memories with emotion weights...")
for text, emotion in memories:
    assistant.add_memory(text, emotion=emotion)

# Query without emotion boost
print("\n=== Query WITHOUT emotion boost ===")
results = assistant.query_memory("What does the user like?", n_results=3, emotion_boost=False)
for i, doc in enumerate(results['documents'][0]):
    meta = results['metadatas'][0][i]
    print(f"{i+1}. {doc} (emotion: {meta.get('emotion', 0):.1f})")

# Query with emotion boost
print("\n=== Query WITH emotion boost ===")
results = assistant.query_memory("What does the user like?", n_results=3, emotion_boost=True)
for i, doc in enumerate(results['documents'][0]):
    meta = results['metadatas'][0][i]
    print(f"{i+1}. {doc} (emotion: {meta.get('emotion', 0):.1f})")

print("\nNotice how emotion boost prioritizes emotionally significant memories!")
