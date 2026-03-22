# BTU Course Assistant MCP

**A Model Context Protocol (MCP) server for searching Brandenburg Technical University (BTU) courses, schedules, and module information from the LSF course management system.**

## Project Overview

The BTU Course Assistant provides AI-powered access to BTU's course catalog through Claude Desktop. It scrapes real-time course data from the BTU LSF (Lehrveranstaltungs-Verwaltungs-System) portal and exposes three main capabilities:

- **Search courses** by keyword and semester
- **Get course schedules** (times, rooms, instructors)
- **Retrieve module descriptions** with ECTS, requirements, and syllabi

## Features

✅ **Async scraping** - Fast, non-blocking concurrent requests to BTU LSF  
✅ **Fallback resilience** - Handles variations in QIS system configurations  
✅ **HTML parsing** - BeautifulSoup-based extraction from complex tables  
✅ **Semester support** - Multiple semesters (SoSe/WiSe 2024-2026)  
✅ **MCP integration** - Seamless Claude Desktop integration  
✅ **Type-safe models** - Pydantic models for courses, schedules, and modules  

## Architecture

```
User (Claude Desktop)
    ↓
MCP Tools (server.py)
    ├── search_btu_courses()
    ├── get_course_schedule()
    └── get_btu_module_info()
         ↓
Scraper Functions (scrapers/lsf.py)
    ├── search_courses()
    ├── get_schedule()
    └── get_module_info()
         ↓
HTTP Fetch (httpx)
    ↓
BTU LSF Portal (https://lsf.b-tu.de/qisserver/rds)
    ↓
HTML Parsing (BeautifulSoup)
    ↓
Data Extraction
    ├── Build search parameters
    ├── Parse HTML tables
    ├── Extract text fields
    └── Clean & normalize data
         ↓
Pydantic Models (models.py)
    ├── Course
    ├── Schedule
    └── ModuleInfo
         ↓
Formatted Response (Markdown)
    ↓
User
```

## How It Works

### 1. Course Search Flow
When searching for courses (e.g., "Mathematik" in SoSe2026):
1. Resolve semester to its internal ID (e.g., "20261")
2. Build multiple parameter sets (handles different QIS configurations)
3. Fetch HTML from BTU LSF via httpx (async)
4. Parse HTML with BeautifulSoup, find course tables
5. Extract course ID, name, lecturer, type, ECTS
6. Return structured data

### 2. Schedule Retrieval
When getting a course schedule by ID:
1. Build course detail parameters with course ID
2. Fetch course page HTML
3. Find schedule table (look for "Tag", "Zeit", "Raum", "Rhythmus")
4. Extract day, time range, room, recurrence pattern
5. Return Schedule object

### 3. Module Information
When looking up a module by number:
1. Build module parameters with module number
2. Fetch module page HTML
3. Parse module metadata table
4. Extract name, ECTS, exam type, prerequisites, description
5. Return ModuleInfo object

## Tools

### `search_btu_courses(query, semester="SoSe2026")`
Search for courses by keyword.

**Parameters:**
- `query` (str): Search term (e.g., "machine learning", "Mathematik", "AI")
- `semester` (str): Semester key (default: "SoSe2026")

**Returns:** List of matching courses with ID, name, lecturer, type, ECTS, and URL

**Example:** `search_btu_courses("Datenbanken", "SoSe2026")`

**Supported semesters:** `SoSe2026`, `SoSe2025`, `WiSe2025`, `SoSe2024`, `WiSe2024`

### `get_course_schedule(course_id)`
Get room and time schedule for a specific course.

**Parameters:**
- `course_id` (str): The course ID from search results

**Returns:** Day, time, room, and recurrence pattern

**Example:** `get_course_schedule("12345678")`

### `get_btu_module_info(module_number)`
Get module description by BTU module number.

**Parameters:**
- `module_number` (str): BTU module number (e.g., "11255")

**Returns:** Module name, ECTS, exam type, prerequisites, description, and URL

**Example:** `get_btu_module_info("11255")`

## Setup & Installation

### Prerequisites
- Python 3.8+
- macOS (for homebrew) or adapt paths for Linux/Windows

### Install

```bash
# Create virtual environment
/opt/homebrew/bin/python3 -m venv .venv

# Install dependencies
./.venv/bin/python -m pip install -r requirements.txt
```

### Test Locally

```bash
./.venv/bin/python test.py
```

### Run MCP Server

```bash
./.venv/bin/python server.py
```

## Claude Desktop Integration

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
	"mcpServers": {
		"btu-course-assistant": {
			"command": "/absolute/path/to/btu-course-mcp/.venv/bin/python",
			"args": ["/absolute/path/to/btu-course-mcp/server.py"]
		}
	}
}
```

**Then restart Claude Desktop.** The server will load on next launch.

## Configuration

Edit `config.py` to customize:

```python
BASE_URL = "https://lsf.b-tu.de/qisserver/rds"  # BTU LSF endpoint

SEMESTER_IDS = {
    "SoSe2026": "20261",  # Summer 2026
    "WiSe2025": "20252",  # Winter 2025-26
    # Add more as needed
}

DEFAULT_SEMESTER = "SoSe2026"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; BTU-Course-Assistant/1.0)"
}
```

## Project Structure

```
btu-course-mcp/
├── server.py              # FastMCP entry point & tool registration
├── config.py              # Configuration (URL, semesters, headers)
├── models.py              # Pydantic data models (Course, Schedule, ModuleInfo)
├── requirements.txt       # Python dependencies
├── test.py                # Integration tests & manual checks
├── README.md              # This file
└── scrapers/
    ├── __init__.py
    ├── lsf.py             # Core LSF scraping & parsing logic
    └── parser.py          # HTML parsing helpers (clean_text, get_page_title)
```

## Dependencies

- **httpx** - Async HTTP client
- **beautifulsoup4** - HTML parsing
- **pydantic** - Data validation
- **fastmcp** - MCP server framework

See `requirements.txt` for versions.

## Development Notes

### HTML Parsing Challenges
- BTU LSF is a QIS system with variations across installations
- Table structure is inconsistent; uses heuristics to find correct tables
- Special tokens like "Tag", "Zeit", "Raum" identify schedule tables

### Fallback Strategy
- Multiple parameter sets allow compatibility with different QIS configs
- First successful request returns results; others are skipped
- Fallback sources (e.g., faculty planning pages) for course search

### Error Handling
- HTTP errors gracefully fall back to next parameter set
- Empty results return empty lists (no exceptions)
- Network timeouts handled with 20-second timeout

### Testing
Run `test.py` to:
- Verify environment setup
- Test course search functionality
- Check semester mapping
- Validate course parsing

## Troubleshooting

### Empty Search Results
1. Verify semester ID is correct in `SEMESTER_IDS`
2. Check that `DEFAULT_SEMESTER` matches an available semester
3. Inspect raw HTML with browser dev tools to understand table structure
4. Add print statements to `_parse_course_search_results()` to debug

### Schedule Not Found
1. Ensure course ID from search results is correct
2. Some courses may not have published schedules
3. Check if page structure differs; may need HTML inspection

### Server Won't Start
1. Verify `requirements.txt` is installed: `./.venv/bin/pip list`
2. Check Python version: `./.venv/bin/python --version`
3. Examine error logs for missing modules
4. Restart Claude Desktop after config changes

## Future Enhancements
- Caching layer for popular courses
- Grade distribution data
- Instructor profiles
- Course prerequisites graph
- Calendar export (.ics)

## License & Credits
Built with [FastMCP](https://github.com/jmanhype/fastmcp) and [BeautifulSoup4](https://www.crummy.com/software/BeautifulSoup/).

---

**For issues or improvements, check the LSF structure and update parsing logic in `scrapers/lsf.py`.**
