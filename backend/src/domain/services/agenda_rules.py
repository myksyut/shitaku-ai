from collections.abc import Sequence

from src.domain.entities.agenda import AgendaTopic
from src.domain.entities.team_memory import ActionItem, OpenIssue


def _action_metadata(action: ActionItem) -> str:
    details = "、".join(
        f"{label}: {value}" for label, value in (("担当", action.assignee_email), ("期限", action.due_on)) if value
    )
    return f"（{details}）" if details else ""


def render_agenda(
    topics: Sequence[AgendaTopic], actions: Sequence[ActionItem], issues: Sequence[OpenIssue], proposal: str | None
) -> str:
    """Keep every required item even when the model contributes nothing."""
    sections = [
        "## 事前に投稿された議題",
        *[f"- {t.title}（{t.author_label}）: {t.details or ''}" for t in topics],
        "## 持ち越しのアクションアイテム",
        *[f"- {a.body}{_action_metadata(a)}: {a.carry_over}回持ち越し" for a in actions],
        "## 未解決の論点",
        *[f"- {i.body}: {i.carry_over}回持ち越し" for i in issues],
        "## 議論の提案",
        proposal.strip() if proposal else "",
    ]
    return "\n".join(sections)
