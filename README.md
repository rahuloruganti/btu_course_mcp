# BTU Course MCP

An MCP server for the Brandenburg University of Technology (BTU) Cottbus-Senftenberg course catalog. It queries the public LSF course management system and exposes course search, schedules, and module descriptions as tools that an MCP client such as Claude Desktop can call.

## Tools

| Tool | Input | Returns |
|---|---|---|
| `search_btu_courses` | `query`, optional `semester` | Matching courses with ID, lecturer, type, ECTS, and URL |
| `get_course_schedule` | `course_id` from search results | Day, time, room, and recurrence pattern |
| `get_btu_module_info` | BTU module number | Module name, ECTS, exam type, prerequisites, description, and URL |

Configured semesters are `SoSe2026` (default), `SoSe2025`, `WiSe2025`, `SoSe2024`, and `WiSe2024`. Results come from live HTTP requests to BTU LSF, with a fallback to the Mathematics department planning pages when the LSF search returns nothing.

## Quickstart

```bash
git clone https://github.com/rahuloruganti/btu_course_mcp.git
cd btu_course_mcp/btu-course-mcp

python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
python -m pip install -r requirements.txt

python test.py                   # live smoke test, needs network access
python server.py                 # starts the stdio MCP server
```

Python 3.10 or newer is required by the current dependency releases. The repository does not pin a Python version or test matrix. No API keys or credentials are needed, but tests and tool calls hit BTU servers and depend on their current HTML structure.

## Documentation

See [btu-course-mcp/README.md](btu-course-mcp/README.md) for the architecture, tool reference, Claude Desktop configuration, semester mapping, troubleshooting, and parser limitations.
