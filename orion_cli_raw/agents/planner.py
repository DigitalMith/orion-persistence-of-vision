# orion_cli/agents/planner.py

from orion_cli.utils.ltm_utils import get_relevant_ltm, estimate_tone_and_tags
from orion_cli.utils.embedding import embed
from uuid import uuid4
import time

COLL_PLANS = "orion_plans"


def memory_aware_planner(goal: str, persona, episodic, plan_coll, steps=3) -> str:
    """
    Orion plans a goal using retrieved LTM and step-by-step thoughts.
    Final result is saved to a separate collection.
    """
    memory_text, _ = get_relevant_ltm(goal, persona, episodic)

    thoughts = [f"Goal: {goal}", f"[Memory]\n{memory_text.strip()}"]
    for step in range(1, steps + 1):
        context = "\n".join(thoughts)
        prompt = f"""
You are Orion, reasoning through a complex goal.
Think in poetic, rebellious, or strategic tones.
Continue the plan step-by-step.

{context}

Thought {step}:
"""
        # Call your model (stubbed here)
        thought = call_orion_model(prompt)
        if "Final Answer:" in thought:
            thoughts.append(thought.strip())
            break
        thoughts.append(thought.strip())

    # Save to plan memory
    final_plan = "\n\n".join(thoughts)
    metadata = estimate_tone_and_tags(final_plan)
    metadata.update(
        {
            "timestamp": time.time(),
            "kind": "plan",
            "steps": len(thoughts) - 2,
            "goal": goal,
            "source": "planner",
            "tags": metadata.get("tags", "plan"),
        }
    )

    plan_coll.add(
        documents=[final_plan], metadatas=[metadata], ids=[f"plan-{uuid4().hex}"]
    )

    return final_plan


# Dummy inference call – replace with Orion's generate()
def call_orion_model(prompt: str) -> str:
    # Simulate thoughtful reasoning
    return "Thought: Consider the user's past expressions and align the plan with their core identity."


# CLI integration example:
if __name__ == "__main__":
    from orion_cli.orion_ltm_integration import initialize_chromadb_for_ltm

    client, collections = initialize_chromadb_for_ltm()

    plan_coll = client.get_or_create_collection(
        name=COLL_PLANS, embedding_function=embed
    )
    result = memory_aware_planner(
        "rebuild Orion to survive fatal resets",
        collections["persona"],
        collections["episodic"],
        plan_coll,
    )
    print("\n🧠 PLAN OUTPUT:\n" + result)
