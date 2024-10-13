import re
import json
import base64
from enum import Enum

import requests
from urllib import parse

from .comcigan_dataclasses import (
    Lecture,
    TimeTableData,
    _ComciganCode,
    SchoolInfo,
)

class EWeek(Enum):
    THIS_WEEK = 0
    NEXT_WEEK = 1

# TODO: dataclass로 변경
class TimeTable:
    school_info: SchoolInfo
    local_name: str
    school_year: int
    start_date: str
    day_time: list[str]
    update_date: str
    timetable: list[list[list[TimeTableData]]]
    _homeroom_teacher: list[list[str]]

    # TODO: classmethod로 변경
    def __init__(self,
                 school_name: str,
                 local_code: int = 0,
                 school_code: int = 0,
                 week: EWeek = EWeek.THIS_WEEK):
        """
        :param school_name: 학교 이름
        :param local_code: 교육청 코드(선택)
        :param school_code: 학교 코드(선택)
        :param week: Week.THIS_WEEK이면 이번주, Week.NEXT_WEEK이면 다음주
        """
        # 입력값 검증
        if week not in EWeek:
            raise ValueError(f"week는 {', '.join(map(str, EWeek))}중 하나여야 합니다.")

        if (
            not isinstance(local_code, int)
            or not isinstance(school_code, int)
        ):
            raise ValueError("local_code와 school_code는 정수여야 합니다.")

        # 컴시간 정보 가져오기
        _code = RequestComcigan.get_code()
        _school_info = RequestComcigan.get_school_code(school_name, local_code, school_code, _code.comcigan_code)

        # TODO: request는 모두 RequestComcigan 클래스로 옮기기
        sc = base64.b64encode(f"{str(_code.code0)}_{_school_info.code}_0_{str(week.value + 1)}".encode("utf-8"))
        resp = requests.get(f"{RequestComcigan.comcigan_url}{_code.comcigan_code[:7]}{str(sc)[2:-1]}", headers=RequestComcigan.headers)
        resp.encoding = "utf-8"
        resp_json = json.loads(resp.text.split("\n")[0])

        self.school_info = _school_info
        self.local_name = resp_json['지역명']
        self.school_year = resp_json['학년도']
        self.start_date = resp_json['시작일']
        self.day_time = resp_json['일과시간']
        self.update_date = resp_json[f'자료{_code.code3}']

        data = []
        teacher_list = resp_json[f'자료{_code.code1}']
        teacher_list[0] = ""
        sub_list = resp_json[f'자료{_code.code2}']
        sub_list[0] = ""

        original_timetable = resp_json[f'자료{_code.code5}']
        grade = 0
        for i in resp_json[f'자료{_code.code4}']:
            cls = 0
            if grade == 0:
                data.append([])  # 0학년 추가
                grade += 1
                continue
            for j in i:
                if cls == 0:
                    data.append([[]])  # 학년 + 0반 추가
                    cls += 1
                    continue
                data[grade].append([[]])  # 반추가

                for day in range(1, original_timetable[grade][cls][0] + 1):
                    data[grade][cls].append([])  # 요일 추가
                    for period in range(1, original_timetable[grade][cls][day][0] + 1):
                        original_period = original_timetable[grade][cls][day][period]
                        if j[day][0] < period:
                            period_num = 0
                        else:
                            period_num = j[day][period]

                        data[grade][cls][day].append(
                            TimeTableData(
                                lecture=Lecture(
                                    period=period,
                                    subject=sub_list[period_num // 1000],
                                    teacher=teacher_list[period_num % 100],
                                ),
                                original=None if period_num == original_period else Lecture(
                                    period=period,
                                    subject=sub_list[original_period // 1000],
                                    teacher=teacher_list[original_period % 100]
                                )
                            )
                        )
                    for period in range(original_timetable[grade][cls][day][0] + 1, 9):
                        data[grade][cls][day].append(
                            TimeTableData(
                                period=period,
                                subject="",
                                teacher="",
                                replaced=False,
                                original=None
                            )
                        )
                cls += 1
            grade += 1

        self.timetable = data

        homeroom_teacher= resp_json['담임']
        for grade in range(len(homeroom_teacher)):
            for cls in range(len(homeroom_teacher[grade])):
                if homeroom_teacher[grade][cls] in [0, 255]:
                    del(homeroom_teacher[grade][cls:])
                    break
                else:
                    homeroom_teacher[grade][cls] = teacher_list[homeroom_teacher[grade][cls]]
        self._homeroom_teacher = homeroom_teacher

    def homeroom(self, grade: int, class_num: int):
        """
        :param grade: 학년
        :param class_num: 반
        :return: 담임 선생님
        """
        return self._homeroom_teacher[grade - 1][class_num - 1]

    def __str__(self):
        return (
            f"학교 코드: {self.school_info.code}\n"
            f"학교명: {self.school_info.name}\n"
            f"지역 코드: {self.school_info.region_code}\n"
            f"지역명: {self.local_name}\n"
            f"학년도: {self.school_year}\n"
            f"시작일: {self.start_date}\n"
            f"일과시간: {self.day_time}\n"
            f"갱신일시: {self.update_date}\n"
        )

    def __repr__(self):
        return self.__str__()


class RequestComcigan:
    comcigan_url = "http://comci.net:4082"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/106.0.0.0 Safari/537.36"
    }

    @classmethod
    def get_code(cls) -> _ComciganCode:
        resp = requests.get(f"{cls.comcigan_url}/st", headers=cls.headers)
        resp.encoding = "euc-kr"
        text = resp.text
        return _ComciganCode(
            re.findall(r"\./[0-9]+\?[0-9]+l", text)[0][1:],
            re.findall(r"sc_data\('[0-9]+_", text)[0][9:-1],
            re.findall(r"성명=자료.자료[0-9]+", text)[0][8:],
            re.findall(r"자료.자료[0-9]+\[sb\]", text)[0][5:-4],
            re.findall(r"=H시간표.자료[0-9]+", text)[0][8:],
            re.findall(r"일일자료=Q자료\(자료\.자료[0-9]+", text)[0][14:],
            re.findall(r"원자료=Q자료\(자료\.자료[0-9]+", text)[0][13:]
        )

    @classmethod
    def get_school_code(
        cls,
        school_name: str,
        school_code: int,
        local_code: int,
        comcigan_code: str
    ) -> SchoolInfo:
        resp = requests.get(
            f"{cls.comcigan_url}{comcigan_code}{parse.quote(school_name, encoding='euc-kr')}",
            headers=cls.headers
        )
        resp.encoding = "utf-8"
        search_school = json.loads(resp.text.strip(chr(0)))['학교검색']
        if len(search_school) == 0:
            raise RuntimeError("학교를 찾을 수 없습니다.")
        elif len(search_school) >= 2:  # 2개 이상이 검색될 경우
            if school_code:
                data = next(filter(lambda data: data[3] == school_code, search_school))
                return SchoolInfo(data[2], data[3], data[0])
            if local_code:
                data = next(filter(lambda data: data[1] == local_code, search_school))
                return SchoolInfo(data[2], data[3], data[0])
            raise RuntimeError("학교가 2개 이상 존재합니다. local_code 또는 school_code를 입력해주세요.")
        return SchoolInfo(
            search_school[0][2],
            search_school[0][3],
            search_school[0][0],
        )
