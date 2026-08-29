"""
Generates an animated SVG snake/pulse that travels across your GitHub
contribution graph, rendered as a self-contained SVG file.
"""
import os
import sys
import json
import datetime
import urllib.request

GITHUB_GRAPHQL_URL = "https://api.github.com/graphql"

QUERY = """
query($userName: String!) {
  user(login: $userName) {
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays {
            date
            contributionCount
            color
          }
        }
      }
    }
  }
}
"""

COLORS = {
    0: "#161B22",
    1: "#1B2A4A",
    2: "#2A3F7A",
    3: "#4F6AF5",
    4: "#7C5CFC",
}
GLOW_COLOR = "#A78BFA"
BG_COLOR = "#07091A"
TEXT_COLOR = "#E0E7FF"

CELL = 11
GAP = 3
LEFT_PAD = 30
TOP_PAD = 40


def fetch_contributions(username: str, token: str) -> list:
    body = json.dumps({"query": QUERY, "variables": {"userName": username}}).encode()
    req = urllib.request.Request(
        GITHUB_GRAPHQL_URL,
        data=body,
        headers={
            "Authorization": f"bearer {token}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read())

    weeks = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
    return weeks


def level_for_count(count: int) -> int:
    if count == 0:
        return 0
    if count <= 2:
        return 1
    if count <= 5:
        return 2
    if count <= 9:
        return 3
    return 4


def build_svg(weeks: list) -> str:
    num_weeks = len(weeks)
    width = LEFT_PAD + num_weeks * (CELL + GAP) + 20
    height = TOP_PAD + 7 * (CELL + GAP) + 20

    cells_svg = []
    pulse_path_points = []

    for w_idx, week in enumerate(weeks):
        for day in week["contributionDays"]:
            count = day["contributionCount"]
            level = level_for_count(count)
            x = LEFT_PAD + w_idx * (CELL + GAP)
            d_idx = week["contributionDays"].index(day)
            y = TOP_PAD + d_idx * (CELL + GAP)

            color = COLORS[level]
            cells_svg.append(
                f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" '
                f'rx="2" fill="{color}" data-date="{day["date"]}" data-count="{count}">'
                f'<animate attributeName="opacity" values="0;1" dur="0.4s" '
                f'begin="{(w_idx * 0.02):.2f}s" fill="freeze" />'
                f'</rect>'
            )

            if count > 0:
                cx = x + CELL / 2
                cy = y + CELL / 2
                pulse_path_points.append((cx, cy))

    pulse_svg = ""
    if pulse_path_points:
        step = max(1, len(pulse_path_points) // 60)
        sampled = pulse_path_points[::step]
        values_x = ";".join(f"{p[0]:.1f}" for p in sampled)
        values_y = ";".join(f"{p[1]:.1f}" for p in sampled)
        total_dur = "18s"

        pulse_svg = f"""
    <circle r="4" fill="{GLOW_COLOR}" opacity="0.9">
      <animate attributeName="cx" values="{values_x}" dur="{total_dur}" repeatCount="indefinite" />
      <animate attributeName="cy" values="{values_y}" dur="{total_dur}" repeatCount="indefinite" />
    </circle>
    <circle r="8" fill="{GLOW_COLOR}" opacity="0.25">
      <animate attributeName="cx" values="{values_x}" dur="{total_dur}" repeatCount="indefinite" />
      <animate attributeName="cy" values="{values_y}" dur="{total_dur}" repeatCount="indefinite" />
      <animate attributeName="r" values="6;10;6" dur="1.2s" repeatCount="indefinite" />
    </circle>
"""

    total_contribs = sum(
        day["contributionCount"] for week in weeks for day in week["contributionDays"]
    )

    svg = f"""<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <filter id="softGlow" x="-50%" y="-50%" width="200%" height="200%">
      <feGaussianBlur stdDeviation="3" result="blur" />
      <feMerge>
        <feMergeNode in="blur" />
        <feMergeNode in="SourceGraphic" />
      </feMerge>
    </filter>
  </defs>

  <rect width="{width}" height="{height}" fill="{BG_COLOR}" rx="8" />

  <text x="{LEFT_PAD}" y="22" fill="{TEXT_COLOR}" font-family="'Courier New', monospace" font-size="13" font-weight="bold">
    {total_contribs} contributions &#183; rolling 52-week activity
  </text>

  {''.join(cells_svg)}

  <g filter="url(#softGlow)">
    {pulse_svg}
  </g>
</svg>
"""
    return svg


def main():
    username = os.environ.get("GITHUB_USERNAME")
    token = os.environ.get("GH_TOKEN")

    if not username or not token:
        print("Set GITHUB_USERNAME and GH_TOKEN environment variables.", file=sys.stderr)
        sys.exit(1)

    weeks = fetch_contributions(username, token)
    svg = build_svg(weeks)

    os.makedirs("output", exist_ok=True)
    with open("output/activity-pulse.svg", "w") as f:
        f.write(svg)

    print(f"Generated output/activity-pulse.svg ({datetime.date.today()})")


if __name__ == "__main__":
    main()
