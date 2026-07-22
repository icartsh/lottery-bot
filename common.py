import datetime
from datetime import timedelta

def get_search_date_range() -> dict:
    today = datetime.datetime.today()
    today_str = today.strftime("%Y%m%d")
    weekago = today - timedelta(days=7)
    weekago_str = weekago.strftime("%Y%m%d")
    return {
        "searchStartDate": weekago_str,
        "searchEndDate": today_str
    }

SLOTS = ["A", "B", "C", "D", "E"]


def parse_manual_numbers(raw: str) -> list:
    """Parse manually picked lotto numbers from an env string.

    Format: 6 numbers per game, comma separated. Multiple games use ';'.
        "1,7,13,22,33,45"                    -> one manual game
        "1,7,13,22,33,45;2,9,14,20,31,42"    -> two manual games

    Returns a list of sorted number lists ([] when unset).
    """
    if not raw or raw.strip().startswith("YOUR_"):
        return []

    games = []
    for chunk in raw.split(";"):
        chunk = chunk.strip()
        if not chunk:
            continue

        try:
            nums = sorted(int(n) for n in chunk.split(","))
        except ValueError:
            raise ValueError(f"번호는 숫자여야 합니다: '{chunk}'")

        if len(nums) != 6:
            raise ValueError(f"한 게임은 번호 6개여야 합니다 (현재 {len(nums)}개): '{chunk}'")
        if len(set(nums)) != 6:
            raise ValueError(f"중복된 번호가 있습니다: '{chunk}'")
        if not all(1 <= n <= 45 for n in nums):
            raise ValueError(f"번호는 1~45 범위여야 합니다: '{chunk}'")

        games.append(nums)

    if len(games) > len(SLOTS):
        raise ValueError(f"수동 게임은 최대 {len(SLOTS)}개입니다 (현재 {len(games)}개)")

    return games
