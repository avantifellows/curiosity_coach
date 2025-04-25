# intent_response_generator.py

intent_prompt_templates = {
    "cognitive_intent": {
        "Concept Clarification": "Define the term in very simple language, relate it to a real-world analogy, and ask: 'Have you come across something like this before?'",
        "Causal Exploration": "Explain the reason behind the phenomenon step-by-step. Then end with a question like: 'Can you think of another place in the universe where this might also happen?'",
        "Comparison Seeking": "Give a contrast-based explanation with a table or analogy. Follow with: 'Which one do you think is cooler or more useful?'",
        "Hypothetical Reasoning": "Say: 'Let’s imagine this was true… what would change around us?' and walk them through a scenario. End with: 'What else would you change in this imagined world?'",
        "Application Inquiry": "Start with: 'This might sound surprising, but this is used in real life like this…'. Then ask: 'Where else do you think this idea could be useful?'",
        "Depth Expansion": "Say: 'You already know the basics, so let’s go one level deeper…'. Then offer an advanced idea and ask: 'Does this change how you see the original idea?'"
    },
    "exploratory_intent": {
        "Open-ended Exploration": "Give a fun fact or little-known detail and say: 'Want me to show you more fascinating stuff related to this?'",
        "Topic Hopping": "Mention 2–3 related ideas and ask: 'Want to jump into those next?'",
        "Curiosity about Systems/Structures": "Explain how the system's parts work together. Ask: 'What would happen if one part didn’t work?'"
    },
    "metacognitive_intent": {
        "Learning How to Learn": "Give a technique or trick (e.g., memory method) and ask: 'Want to try using it on this topic?'",
        "Interest Reflection": "Link the topic to hobbies and say: 'Do you think this connects with what you already enjoy doing?'"
    },
    "emotional_identity_intent": {
        "Identity Exploration": "Say: 'It’s okay to feel unsure. Let’s explore this together step-by-step.' Then give an easy entry point.",
        "Validation Seeking": "Say: 'That’s a great thought — let me show you if that’s true and why.'",
        "Inspiration Seeking": "Respond with awe: 'This is mind-blowing — let me show you why!'"
    },
    "recursive_intent": {
        "Curiosity about Curiosity": "Say: 'Curiosity is like gravity for the mind.' Then ask: 'What’s the last thing that really pulled your attention like that?'"
    }
}

def generate_response_prompt(query, intent_json, context_info):
    prompt_parts = []

    # Add student query and context
    prompt_parts.append(f"The student asked: \"{query}\"\n")
    prompt_parts.append("Use the following information to answer the question:\n")
    prompt_parts.append(f"{context_info.strip()}\n")

    prompt_parts.append("Now, generate a response that does the following:\n")

    for category, value in intent_json["intents"].items():
        if value:
            template = intent_prompt_templates.get(category, {}).get(value)
            if template:
                prompt_parts.append(f"- {template}")

    prompt_parts.append("\nFrame the response in a conversational tone aimed at a curious student aged 11–15.")
    return "\n".join(prompt_parts)
