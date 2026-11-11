# Swarm plugins, MCP and shared skills

Definitions here are **integration plans**, not evidence that a server or plugin is connected.

| Integration | Purpose | Mode |
|---|---|---|
| Connected GitHub plugin/app | Repository read, PR creation, Actions verification | First choice in ChatGPT |
| Official `github/github-mcp-server` | Local Codex/Claude developer tools | Read-only default; narrowly scoped |
| ContinuityOS | Cost-aware coding-agent routing, isolation, PR orchestration | Optional; verify before calling |
| `github.com/coden607/skills` | Canonical reusable skills | Load smallest SKILL.md for task |
| DigitalOcean / SSH / Tailscale | Server diagnostics, only if actually deployed | Read-only without owner approval |
| Gemini model API | Optional frame-based counting | Disabled for privacy-sensitive dev |
| Cloudflare tunnel | Optional remote access | Disabled until approved |
| SMTP / browser and Web Push | Alerts | Explicit setup and recipients |
| Supabase / Vercel / Stripe / RAG / Mem0 / n8n / Archon / Paperclip / LiteLLM | Not present as runtime dependencies | Do not install speculatively |

## Official GitHub MCP local example
Source: https://github.com/github/github-mcp-server . Host must already have Docker, a limited GitHub token in local environment, and an MCP-capable client. This is **not installed by this PR**.

```sh
docker run -i --rm \
  -e GITHUB_PERSONAL_ACCESS_TOKEN \
  -e GITHUB_READ_ONLY=1 \
  -e GITHUB_TOOLSETS=repos,pull_requests,actions \
  ghcr.io/github/github-mcp-server
```

Do not paste tokens in agent chat or commit them to config. On GitHub Copilot's hosted environment, the built-in GitHub MCP is already read-only on the repo by default; wider access requires deliberate configuration.

## Tool boundary
Default agents can read public code and test outcomes. Implementer may write **new branch and PR** after task authorization. Owner alone approves merge, changes to production, public tunnel, camera device access, secrets, signing, billing, external communication or image transfer. Use only synthetic test frames in agents. A policy file or prompt alone is not a security sandbox.

`config/agent-tool-policy.json` describes the intended role permissions. Its controls are **advisory**, not actually enforced by the Python app or an MCP proxy.
