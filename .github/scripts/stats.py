"""Rewrite the stats line in README.md from the GitHub contribution calendar (includes private contributions)."""
import datetime as dt
import json
import os
import re
import urllib.request

USER = "c1b3r-p3d1a"
QUERY = """{user(login:"%s"){createdAt pullRequests(states:MERGED){totalCount}
contributionsCollection{contributionCalendar{totalContributions weeks{contributionDays{date contributionCount}}}}}}""" % USER


def streaks(days):
    """days: list of (date_str, count) sorted ascending -> (current, longest). Today with 0 doesn't break the streak."""
    longest = run = 0
    for _, n in days:
        run = run + 1 if n else 0
        longest = max(longest, run)
    current = 0
    for i, (_, n) in enumerate(reversed(days)):
        if n:
            current += 1
        elif i:  # a zero today is allowed, the day isn't over yet
            break
    return current, longest


assert streaks([("a", 1), ("b", 0), ("c", 2), ("d", 3), ("e", 0)]) == (2, 2)
assert streaks([("a", 1), ("b", 1), ("c", 0), ("d", 1)]) == (1, 2)


def main():
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY}).encode(),
        headers={"Authorization": "bearer " + os.environ["GITHUB_TOKEN"]},
    )
    user = json.load(urllib.request.urlopen(req))["data"]["user"]
    cal = user["contributionsCollection"]["contributionCalendar"]
    days = [(d["date"], d["contributionCount"]) for w in cal["weeks"] for d in w["contributionDays"]]
    current, longest = streaks(days)
    years = dt.date.today().year - int(user["createdAt"][:4])

    line = (
        f"Joined GitHub **{years}** years ago · **{cal['totalContributions']}** contributions in the last year · "
        f"**{user['pullRequests']['totalCount']}** merged pull requests · "
        f"**{current}**-day streak (best **{longest}**)"
    )
    readme = open("README.md", encoding="utf-8").read()
    new = re.sub(r"(<!-- stats -->\n).*?(\n<!-- /stats -->)", lambda m: m[1] + line + m[2], readme, flags=re.S)
    open("README.md", "w", encoding="utf-8", newline="\n").write(new)


if __name__ == "__main__":
    main()
