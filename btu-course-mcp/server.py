from fastmcp import FastMCP

from config import SEMESTER_IDS
from scrapers.lsf import get_module_info, get_schedule, search_courses

mcp = FastMCP("BTU Course Assistant")


@mcp.tool()
async def search_btu_courses(query: str, semester: str = "SoSe2026") -> str:
    """
    Search for BTU courses by keyword.

    Args:
        query: Search term such as 'machine learning', 'Mathematik', or 'AI'.
        semester: Semester key, for example 'SoSe2026' or 'WiSe2025'.

    Returns:
        List of matching courses with name, lecturer, type and ECTS.
    """
    if semester not in SEMESTER_IDS:
        choices = ", ".join(SEMESTER_IDS.keys())
        return f"Invalid semester. Choose from: {choices}"

    courses = await search_courses(query, semester)
    if not courses:
        return f"No courses found for '{query}' in {semester}."

    lines = [f"Found {len(courses)} course(s) for '{query}' in {semester}:", ""]
    for c in courses:
        lines.append(f"- [{c.id or 'N/A'}] {c.name}")
        if c.lecturer:
            lines.append(f"  Lecturer: {c.lecturer}")
        if c.course_type:
            lines.append(f"  Type: {c.course_type}")
        if c.day:
            lines.append(f"  Day: {c.day}")
        if c.time_start:
            time_range = f"{c.time_start}"
            if c.time_end:
                time_range += f" – {c.time_end}"
            lines.append(f"  Time: {time_range}")
        if c.place:
            lines.append(f"  Place: {c.place}")
        if c.building:
            lines.append(f"  Building: {c.building}")
        if c.ects:
            lines.append(f"  ECTS: {c.ects}")
        if c.url:
            lines.append(f"  URL: {c.url}")
        lines.append("")

    return "\n".join(lines)


@mcp.tool()
async def get_course_schedule(course_id: str) -> str:
    """
    Get room and time schedule for a specific course.

    Args:
        course_id: The course ID from search results.

    Returns:
        Day, time, room and recurrence for the course.
    """
    schedule = await get_schedule(course_id)
    if not schedule:
        return f"No schedule found for course ID {course_id}."

    return (
        f"Schedule for: {schedule.course_name}\n"
        f"Day:       {schedule.day or 'N/A'}\n"
        f"Time:      {schedule.time_start or '?'} - {schedule.time_end or '?'}\n"
        f"Room:      {schedule.room or 'N/A'}\n"
        f"Rhythm:    {schedule.recurrence or 'N/A'}"
    )


@mcp.tool()
async def get_btu_module_info(module_number: str) -> str:
    """
    Get module description by BTU module number.

    Args:
        module_number: BTU module number, for example '11255'.

    Returns:
        Module name, ECTS, exam type, prerequisites and description.
    """
    info = await get_module_info(module_number)
    if not info:
        return f"No module found with number {module_number}."

    lines = [
        f"Module: {info.name}",
        f"Number: {info.module_number}",
        f"ECTS: {info.ects or 'N/A'}",
        f"Exam: {info.exam_type or 'N/A'}",
        f"Lecturer: {info.lecturer or 'N/A'}",
    ]
    if info.prerequisites:
        lines.append(f"Prerequisites: {info.prerequisites}")
    if info.description:
        lines.append("")
        lines.append(f"Description:\n{info.description[:500]}...")
    if info.url:
        lines.append("")
        lines.append(f"URL: {info.url}")
    return "\n".join(lines)


if __name__ == "__main__":
    mcp.run()
