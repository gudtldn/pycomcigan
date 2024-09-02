from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class Lecture:
    """교과목 정보"""
    period: int
    subject: str
    teacher: str

    def __str__(self):
        return f"{self.period}교시: {self.subject}({self.teacher})"

@dataclass(frozen=True)
class TimeTableData:
    """시간표 데이터"""
    period: int
    subject: str
    teacher: str
    replaced: bool
    original: Optional[Lecture]

    def __str__(self):
        return f"{self.period}교시: {self.subject}({self.teacher}){' (대체)' if self.replaced else ''}"

@dataclass(frozen=True)
class _ComciganCode:
    """컴시간 코드"""
    comcigan_code: str
    code0: str
    code1: str
    code2: str
    code3: str
    code4: str
    code5: str

@dataclass(frozen=True)
class _SchoolInfo:
    """학교 정보"""
    name: str
    code: str
    region_code: str
