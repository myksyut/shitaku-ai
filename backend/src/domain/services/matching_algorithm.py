"""トランスクリプト紐付けアルゴリズム.

Design Doc準拠のスコア計算:
- 会議名の類似度: 0.4 (Levenshtein距離)
- 日時の近さ: 0.3 (+-24時間以内で線形減衰)
- 参加者の一致率: 0.3 (Jaccard係数)
"""

from datetime import datetime


def calculate_string_similarity(str1: str, str2: str) -> float:
    """文字列の類似度を計算する（Levenshtein距離ベース）.

    AC13: ドキュメント名と会議名のマッチング

    Args:
        str1: 文字列1
        str2: 文字列2

    Returns:
        類似度（0.0-1.0）
    """
    if not str1 or not str2:
        return 0.0

    # 小文字に正規化
    s1 = str1.lower()
    s2 = str2.lower()

    if s1 == s2:
        return 1.0

    # 一方が他方に含まれる場合
    if s1 in s2 or s2 in s1:
        shorter = min(len(s1), len(s2))
        longer = max(len(s1), len(s2))
        return shorter / longer

    # Levenshtein距離を計算
    distance = _levenshtein_distance(s1, s2)
    max_len = max(len(s1), len(s2))

    if max_len == 0:
        return 1.0

    similarity = 1.0 - (distance / max_len)
    return max(0.0, similarity)


def _levenshtein_distance(s1: str, s2: str) -> int:
    """Levenshtein距離を計算する."""
    if len(s1) < len(s2):
        return _levenshtein_distance(s2, s1)

    if len(s2) == 0:
        return len(s1)

    previous_row = list(range(len(s2) + 1))

    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]


def calculate_time_score(
    doc_created: datetime,
    event_datetime: datetime,
) -> float:
    """日時の近さスコアを計算する.

    AC14: 日時比較（+-24時間以内で線形減衰）

    Args:
        doc_created: ドキュメント作成日時
        event_datetime: イベント日時

    Returns:
        スコア（0.0-1.0）、24時間以内で線形減衰
    """
    diff_hours = abs((doc_created - event_datetime).total_seconds() / 3600)

    if diff_hours > 24:
        return 0.0

    return 1.0 - (diff_hours / 24)


def calculate_jaccard(set1: set[str], set2: set[str]) -> float:
    """Jaccard係数を計算する.

    AC15: 参加者名と話者名の照合

    Args:
        set1: 集合1
        set2: 集合2

    Returns:
        Jaccard係数（0.0-1.0）
    """
    if not set1 or not set2:
        return 0.0

    intersection = len(set1 & set2)
    union = len(set1 | set2)

    if union == 0:
        return 0.0

    return intersection / union


def extract_name_from_email(email: str) -> str:
    """メールアドレスから名前部分を抽出する.

    Args:
        email: メールアドレス

    Returns:
        名前部分（@より前、小文字）
    """
    return email.split("@")[0].lower()


def calculate_match_confidence(
    doc_name: str,
    doc_created: datetime,
    event_summary: str,
    event_datetime: datetime,
    event_attendees: list[str],
    transcript_speakers: list[str],
) -> float:
    """紐付け信頼度を計算する.

    Design Doc準拠のスコア計算:
    - 会議名の類似度: 0.4 (Levenshtein距離)
    - 日時の近さ: 0.3 (+-24時間以内で線形減衰)
    - 参加者の一致率: 0.3 (Jaccard係数)

    Args:
        doc_name: ドキュメント名
        doc_created: ドキュメント作成日時
        event_summary: イベント名
        event_datetime: イベント日時
        event_attendees: イベント参加者のメールアドレスリスト
        transcript_speakers: トランスクリプトの話者名リスト

    Returns:
        信頼度スコア（0.0-1.0）
    """
    score = 0.0

    # 会議名の類似度（0.4）
    name_similarity = calculate_string_similarity(doc_name, event_summary)
    score += name_similarity * 0.4

    # 日時の近さ（0.3）
    time_score = calculate_time_score(doc_created, event_datetime)
    score += time_score * 0.3

    # 参加者の一致率（0.3）
    # メールアドレスから名前を抽出して比較
    attendee_names = {extract_name_from_email(email) for email in event_attendees}
    speaker_names = {name.lower() for name in transcript_speakers}
    attendee_match = calculate_jaccard(attendee_names, speaker_names)
    score += attendee_match * 0.3

    return score
