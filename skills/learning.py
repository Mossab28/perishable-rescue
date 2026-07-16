"""The learning layer. Risk and Need & Equity read learned_rules.json before they
reason; after each run, learn() appends newly discovered patterns and reinforces
existing ones. runs_completed + times_reinforced make improvement measurable."""
import json
import config


def load_rules() -> dict:
    try:
        return json.loads(config.SKILLS_FILE.read_text())
    except Exception:
        return {"version": 1, "runs_completed": 0, "rules": []}


def rules_for(rules: dict, agent: str) -> list:
    return [r for r in rules.get("rules", []) if r.get("agent") == agent]


def rules_as_text(rules: dict, agent: str) -> str:
    items = rules_for(rules, agent)
    if not items:
        return "(no learned rules yet)"
    return "\n".join(
        f"- [{r['id']} · reinforced x{r.get('times_reinforced', 0)}] {r['rule']}"
        for r in items
    )


def learn(rules: dict, discoveries: list) -> dict:
    """Merge freshly discovered patterns. A discovery matching an existing rule's
    scope+agent reinforces it; otherwise it becomes a new rule. Returns updated dict."""
    rules = dict(rules)
    rules["runs_completed"] = rules.get("runs_completed", 0) + 1
    existing = rules.setdefault("rules", [])
    by_key = {(r.get("agent"), r.get("scope")): r for r in existing}
    next_num = {"risk": 0, "need_equity": 0}
    for r in existing:
        pfx = r["id"][0]
        try:
            n = int(r["id"].split("-")[1])
        except Exception:
            n = 0
        if pfx == "R":
            next_num["risk"] = max(next_num["risk"], n)
        elif pfx == "E":
            next_num["need_equity"] = max(next_num["need_equity"], n)

    for d in discoveries:
        key = (d["agent"], d["scope"])
        if key in by_key:
            r = by_key[key]
            r["times_reinforced"] = r.get("times_reinforced", 0) + 1
            r["confidence"] = round(min(0.99, r.get("confidence", 0.7) + 0.02), 3)
        else:
            next_num[d["agent"]] += 1
            pfx = "R" if d["agent"] == "risk" else "E"
            new = {
                "id": f"{pfx}-{next_num[d['agent']]:03d}",
                "agent": d["agent"],
                "scope": d["scope"],
                "rule": d["rule"],
                "confidence": d.get("confidence", 0.6),
                "source": "learned",
                "times_reinforced": 1,
            }
            existing.append(new)
            by_key[key] = new
    return rules


def save_rules(rules: dict) -> None:
    config.SKILLS_FILE.write_text(json.dumps(rules, indent=2) + "\n")
