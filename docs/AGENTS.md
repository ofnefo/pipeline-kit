# Agent integration

Read `agents/AGENTS.template.md`, adapt it to your workspace, then install it using your agent's normal project instructions mechanism. `agents/model-policy.example.json` records routing preferences; it neither launches agents nor changes billing permissions.

The standalone skills under `skills/` use standard `SKILL.md` frontmatter. Keep their relative links to `modules/` when copying the distribution. They are curated portable adaptations of owned workflows, not copies of plugin caches or personal voice profiles.

Set `PIPELINE_KIT_WORKSPACE` in the agent process environment to the same absolute workspace passed to the panel. Read tasks with:

```sh
python apps/tools/workboard/board.py list
python apps/tools/workboard/board.py get TASK_ID
python apps/tools/workboard/board.py --help
```

The CLI requires the current task version for mutations. The UI's handoff text specifies start, heartbeat, block and evidence-backed submit actions. It does not launch the selected executor.

NameNode is local and requires no Git or SSH. The CLI accepts an action and a JSON object; shell quoting varies by platform. For long card bodies, use the local API `/api/namenode/card` with a structured JSON request. Standard card sections remain Russian to preserve compatibility with the Control editor; see `config/card.example.json`. Claims and journal entries contain only data that the operator or agent deliberately writes.

Keep file and tool permissions bounded to the selected project. The HTTP API is a local single-user interface, not an authorization boundary between different logged-in users. Imported material never authorizes model calls or external delivery.
