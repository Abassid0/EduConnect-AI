from dataclasses import dataclass, field
from typing import Any


@dataclass
class FlowResult:
    reply: dict[str, Any] | None = None
    replies: list[dict[str, Any]] = field(default_factory=list)
    next_step: str | None = None
    next_flow: str | None = None
    flow_data: dict[str, Any] = field(default_factory=dict)
    flow_complete: bool = False

    @property
    def all_replies(self) -> list[dict[str, Any]]:
        result = list(self.replies)
        if self.reply:
            result.append(self.reply)
        return result
