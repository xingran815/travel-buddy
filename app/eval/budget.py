PRICE_PER_1K_INPUT_USD = 0.005
PRICE_PER_1K_OUTPUT_USD = 0.015


class TokenBudget:
    def __init__(self) -> None:
        self.input_tokens = 0
        self.output_tokens = 0
        self.calls = 0

    def add_usage(self, usage) -> None:
        if usage is None:
            return
        self.calls += 1
        self.input_tokens += int(getattr(usage, "prompt_tokens", 0) or 0)
        self.output_tokens += int(getattr(usage, "completion_tokens", 0) or 0)

    def estimate_usd(self) -> float:
        return (
            self.input_tokens / 1000.0 * PRICE_PER_1K_INPUT_USD
            + self.output_tokens / 1000.0 * PRICE_PER_1K_OUTPUT_USD
        )

    def report(self) -> str:
        return (
            f"LLM usage: {self.calls} calls, "
            f"{self.input_tokens} in / {self.output_tokens} out tokens, "
            f"~${self.estimate_usd():.4f}"
        )
