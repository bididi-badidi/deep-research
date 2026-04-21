from agents.prompts import load_prompt


def test_injection():
    print("Testing prompt injection...")

    # Test lead_planning (has 2 references)
    print("\n--- Testing lead_planning ---")
    lead_prompt = load_prompt("lead_planning")
    print(f"Length of lead_planning: {len(lead_prompt)}")
    assert "--- REFERENCE: decomposition-patterns.md ---" in lead_prompt
    assert "--- REFERENCE: synthesis-formats.md ---" in lead_prompt
    print("Found decomposition-patterns and synthesis-formats references.")

    # Test receptionist (has 1 reference)
    print("\n--- Testing receptionist ---")
    recep_prompt = load_prompt("receptionist")
    print(f"Length of receptionist: {len(recep_prompt)}")
    assert "--- REFERENCE: finer-pico-primer.md ---" in recep_prompt
    print("Found finer-pico-primer reference.")

    # Test subagent (has 2 references, including the one we just created)
    print("\n--- Testing subagent ---")
    sub_prompt = load_prompt("subagent", task_id="test-123")
    print(f"Length of subagent: {len(sub_prompt)}")
    assert "--- REFERENCE: source-evaluation-guide.md ---" in sub_prompt
    assert "--- REFERENCE: citation-formats.md ---" in sub_prompt
    assert "test-123" in sub_prompt  # Check variable substitution
    print(
        "Found source-evaluation-guide and citation-formats references. Variable substitution worked."
    )

    # Test lead_synthesis (has 3 references)
    print("\n--- Testing lead_synthesis ---")
    synth_prompt = load_prompt("lead_synthesis")
    print(f"Length of lead_synthesis: {len(synth_prompt)}")
    assert "--- REFERENCE: synthesis-formats.md ---" in synth_prompt
    assert "--- REFERENCE: citation-formats.md ---" in synth_prompt
    assert "--- REFERENCE: source-evaluation-guide.md ---" in synth_prompt
    print(
        "Found synthesis-formats, citation-formats, and source-evaluation-guide references."
    )

    print("\nAll injection tests passed!")


if __name__ == "__main__":
    test_injection()
