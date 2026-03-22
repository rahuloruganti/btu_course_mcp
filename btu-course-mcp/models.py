from typing import Optional

from pydantic import BaseModel


class Course(BaseModel):
    id: str
    name: str
    lecturer: Optional[str] = None
    semester: Optional[str] = None
    course_type: Optional[str] = None
    ects: Optional[str] = None
    url: Optional[str] = None
    day: Optional[str] = None
    time_start: Optional[str] = None
    time_end: Optional[str] = None
    place: Optional[str] = None
    building: Optional[str] = None


class Schedule(BaseModel):
    course_id: str
    course_name: str
    day: Optional[str] = None
    time_start: Optional[str] = None
    time_end: Optional[str] = None
    room: Optional[str] = None
    building: Optional[str] = None
    recurrence: Optional[str] = None


class ModuleInfo(BaseModel):
    module_number: str
    name: str
    description: Optional[str] = None
    ects: Optional[str] = None
    exam_type: Optional[str] = None
    prerequisites: Optional[str] = None
    lecturer: Optional[str] = None
    url: Optional[str] = None
