from collections.abc import Sequence

from src.domain.entities.agenda import AgendaTopic
from src.domain.entities.team_memory import ActionItem, OpenIssue


def _action_metadata(action: ActionItem) -> str:
    details = "、".join(
        f"{label}: {value}" for label, value in (("担当", action.assignee_email), ("期限", action.due_on)) if value
    )
    return f"（{details}）" if details else ""


def _topic_line(topic: AgendaTopic) -> str:
    title = " ".join(topic.title.split())
    author = " ".join(topic.author_label.split())
    details = " ".join((topic.details or "").split())
    return f"- {title}（{author}）: {details}"


def render_agenda(
    topics: Sequence[AgendaTopic], actions: Sequence[ActionItem], issues: Sequence[OpenIssue], proposal: str | None
) -> str:
    """Render the required agenda sections and the optional proposal."""
    sections = [
        "## 事前に投稿された議題",
        *[_topic_line(t) for t in topics],
        "## 持ち越しのアクションアイテム",
        *[f"- {a.body}{_action_metadata(a)}: {a.carry_over}回持ち越し" for a in actions],
        "## 未解決の論点",
        *[f"- {i.body}: {i.carry_over}回持ち越し" for i in issues],
        "## 議論の提案",
        proposal.strip() if proposal else "",
    ]
    return "\n".join(sections)
