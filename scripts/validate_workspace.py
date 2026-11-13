#!/usr/bin/env python3
"""Local, dependency-free AI workspace contract validation."""
import json
from pathlib import Path

root = Path(__file__).resolve().parent.parent
required = (
    "AGENTS.md", "CLAUDE.md", "GEMINI.md",
    ".github/copilot-instructions.md",
    ".github/instructions/backend.instructions.md",
    ".github/instructions/mobile.instructions.md",
    ".github/instructions/installer.instructions.md",
    "docs/agent-workspace.md", "docs/agent-memory.md",
    "docs/environment.md", "docs/integrations.md",
    "docs/chatgpt-project-instructions.md", "docs/security-review.md",
    "config/env.template", "config/agent-tool-policy.json",
    "MISSION.md", "FACTORY_RULES.md", "harness/END-TO-END.md",
)
skills = ("swarm-camera-debug", "swarm-privacy-audit", "swarm-release-review")
errors = []
for name in required:
    if not (root / name).is_file():
        errors.append("missing " + name)
try:
    cfg = json.loads((root / "config/agent-tool-policy.json").read_text())
    if cfg["default_profile"] != "review" or cfg["profiles"]["review"]["write"] != []:
        errors.append("unsafe default tool profile")
    if cfg["kind"] != "advisory-not-enforced":
        errors.append("misleading enforcement claim")
    if set(cfg["local_skills"]) != set(skills):
        errors.append("skill manifest mismatch")
except (OSError, ValueError, KeyError) as exc:
    errors.append("invalid policy: " + str(exc))
for name in skills:
    p = root / ".claude/skills" / name / "SKILL.md"
    if not p.is_file():
        errors.append("missing skill " + name)
    else:
        s = p.read_text()
        if not (s.startswith("---\n") and ("name: " + name + "\n") in s and "description:" in s):
            errors.append("invalid skill frontmatter " + name)
template = root / "config/env.template"
if template.is_file():
    for line in template.read_text().splitlines():
        if line.startswith(("ADMIN_PASS=", "JWT_SECRET=")) and line.split("=", 1)[1].strip():
            errors.append("hardcoded secret in env template")
for name in ("AGENTS.md", "docs/chatgpt-project-instructions.md"):
    p = root / name
    if p.is_file():
        body = p.read_text()
        for token in ("ContinuityOS", "SWARM_DETECTOR=local", "SWARM_REMOTE=0"):
            if token not in body:
                errors.append("missing boundary " + name + ": " + token)
for e in errors:
    print("FAIL:", e)
if errors:
    raise SystemExit(1)
print("PASS: workspace files, skill metadata, default profile, privacy boundaries")
