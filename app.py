import inspect
import json
import logging
from pathlib import Path
import ollama
from tools import calculate_budget, check_resources

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

# Model configuration
MODEL_NAME = "llama3.1"  # Or your chosen Ollama tool-calling model
MAX_STEPS = 5
MAX_RETRIES_PER_TOOL = 1

# Gate 1: Tool Registry / Allowlist
TOOLS = {
    "calculate_budget": calculate_budget,
    "check_resources": check_resources,
}

SYSTEM_PROMPT = """You are a workshop planning assistant.
Objective: Produce a cost estimate and a resource check for the user's request.
Tool-use rules: Use only the declared tools. Never guess numbers a tool can compute.
Constraints: Currency is INR. Do not invent inventory. Do not silently exceed budget.
Missing-data behavior: If an argument is missing, ask for it instead of assuming."""

# Append SKILL.md if present
if Path("SKILL.md").exists():
    SYSTEM_PROMPT += "\n\n" + Path("SKILL.md").read_text()


def validate_args(name: str, args: dict) -> str | None:
    """Gate 2: Argument signature validation before execution."""
    func = TOOLS[name]
    sig = inspect.signature(func)
    params = sig.parameters

    for param_name, param in params.items():
        if param.default == inspect.Parameter.empty and param_name not in args:
            return f"missing required argument: '{param_name}'"

    for arg_name in args:
        if arg_name not in params:
            return f"unexpected argument: '{arg_name}'"

    return None


def dispatch(name: str, args: dict) -> dict:
    """Safe dispatch gatekeeper."""
    # Gate 1: Check Allowlist
    if name not in TOOLS:
        return {"error": f"unknown tool: {name}"}

    # Gate 2: Schema validation
    problem = validate_args(name, args)
    if problem:
        return {"error": problem}

    # Gate 3: Safe execution
    try:
        return TOOLS[name](**args)
    except TypeError as e:
        return {"error": f"bad arguments for {name}: {e}"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}"}


def run_agent(user_query: str) -> str:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_query},
    ]

    tool_declarations = list(TOOLS.values())
    failures: dict[str, int] = {}

    for step in range(MAX_STEPS):
        response = ollama.chat(
            model=MODEL_NAME,
            messages=messages,
            tools=tool_declarations,
        )

        message = response.message
        messages.append(message)

        # Stop condition 1: No tool calls emitted (final answer generated)
        if not message.tool_calls:
            return message.content

        for call in message.tool_calls:
            name = call.function.name
            raw_args = call.function.arguments

            log.info("Step %d: REQUEST %s with %s", step, name, raw_args)
            result = dispatch(name, raw_args)
            log.info("Step %d: RESULT %s -> %s", step, name, result)

            # Failure check & bounded retry limits
            if "error" in result:
                failures[name] = failures.get(name, 0) + 1
                if failures[name] > MAX_RETRIES_PER_TOOL:
                    return f"Stopped: Tool '{name}' failed {failures[name]} times. Error: {result['error']}"

            messages.append({
                "role": "tool",
                "content": json.dumps(result),
            })

    return "Stopped: reached MAX_STEPS limit without final resolution."


if __name__ == "__main__":
    query = (
        "Plan a two-day workshop for 30 students within a ₹15,000 budget, "
        "assuming daily cost per person is 200 INR. "
        "Check availability for projector, Wi-Fi, whiteboard, laptops, and microphones."
    )
    print("\n--- Running Agent ---")
    final_output = run_agent(query)
    print("\n--- Final Agent Summary ---\n")
    print(final_output)