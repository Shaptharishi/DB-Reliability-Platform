from golden_dataset import GOLDEN_DATASET
from main_file import run_agent, AVAILABLE_TOOLS
import json


def evaluate_one(entry):
    """
    Runs the agent against one golden dataset entry and checks
    two things: did it use a reasonable tool, and does the final
    answer contain the expected keywords.
    """
    tool_calls_made = []

    # Temporarily wrap each real tool to record which ones get called,
    # without changing their actual behavior at all.
    original_tools = dict(AVAILABLE_TOOLS)

    def make_recorder(name, real_func):
        def recorder(args):
            tool_calls_made.append(name)
            return real_func(args)
        return recorder

    for name, func in original_tools.items():
        AVAILABLE_TOOLS[name] = make_recorder(name, func)

    answer = run_agent(entry["question"])

    # Restore the real tools afterward, so this recording doesn't
    # leak into any other test run.
    for name, func in original_tools.items():
        AVAILABLE_TOOLS[name] = func

    answer_lower = answer.lower().replace("'", "'").replace("'", "'")
    keyword_hits = [kw for kw in entry["expected_keywords"] if kw in answer_lower]
    keywords_passed = len(keyword_hits) > 0

    tool_passed = True
    if entry["expected_tool"] is not None:
        tool_passed = entry["expected_tool"] in tool_calls_made

    return {
        "question": entry["question"],
        "tool_calls_made": tool_calls_made,
        "expected_tool": entry["expected_tool"],
        "tool_passed": tool_passed,
        "keyword_hits": keyword_hits,
        "keywords_passed": keywords_passed,
        "overall_pass": tool_passed and keywords_passed,
        "answer_preview": answer[:200],
    }


def run_all():
    results = [evaluate_one(entry) for entry in GOLDEN_DATASET]

    passed = sum(1 for r in results if r["overall_pass"])
    total = len(results)

    print(f"\n{'='*60}")
    print(f"RESULTS: {passed}/{total} passed")
    print(f"{'='*60}\n")

    for r in results:
        status = "PASS" if r["overall_pass"] else "FAIL"
        print(f"[{status}] {r['question']}")
        print(f"       Tool used: {r['tool_calls_made']} (expected: {r['expected_tool']})")
        print(f"       Keywords found: {r['keyword_hits']}")
        if not r["overall_pass"]:
            print(f"       Answer preview: {r['answer_preview']}")
        print()

    return results


if __name__ == "__main__":
    run_all()