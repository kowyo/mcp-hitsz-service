from JWLoginClient import JWLoginClient
import json
import csv
import os
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass


@dataclass
class CourseGrade:
    """课程成绩数据类"""
    course_id: str         # 课程代码
    course_name: str       # 课程名称
    course_name_en: str    # 课程英文名称
    credit: float          # 学分
    semester: str          # 学期
    semester_display: str  # 学期显示名称
    score: str             # 总成绩
    score_raw: str         # 原始分数
    exam_type: str         # 考核方式
    course_type: str       # 课程类型 (必修/选修)
    course_category: str   # 课程类别
    department: str        # 开课院系
    is_pass: bool          # 是否及格
    is_restudy: bool       # 是否重修
    rank: str              # 排名
    total_students: str    # 总人数


@dataclass
class GPAInfo:
    """GPA 信息数据类"""
    gpa: float                     # 核心课 GPA
    all_course_gpa: float          # 全部课程 GPA
    avg_score: float               # 核心课平均学分绩
    all_course_avg_score: float    # 全部课程平均学分绩
    rank: int                      # 排名
    total_students: int            # 总人数
    rank_percentage: float         # 排名百分比
    passed_courses: int            # 通过课程数
    total_credits: float           # 获得学分


@dataclass
class SemesterInfo:
    """学期信息数据类"""
    academic_year: str      # 学年，如"2025-2026"
    semester_code: str      # 学期代码，如"1"
    year_name: str          # 年份名称，如"2025"
    semester_name: str      # 学期名称，如"秋季"
    year_name_en: str       # 年份英文名称，如"2025"
    semester_name_en: str   # 学期英文名称，如"Fall"


@dataclass
class CurrentSemester:
    """当前学年学期数据类"""
    academic_year: str      # 学年，如"2024-2025"
    semester_full_code: str # 完整学期编码，如"2024-20252"
    semester_code: str      # 学期代码，如"2"


@dataclass
class TeachingBuilding:
    """教学楼信息数据类"""
    name: str               # 教学楼名称，如"A 楼"
    code: str               # 教学楼代码，如"01"
    name_en: Optional[str]  # 教学楼英文名称，如"Teaching Building II"


@dataclass
class ClassroomInfo:
    """教室信息数据类"""
    name: str               # 教室名称，如"T5204"
    code: str               # 教室代码，如"T5204"
    name_en: str            # 教室英文名称
    seats: int              # 座位数
    is_available: bool      # 是否可借用
    is_movable_seats: bool  # 座椅是否可移动
    is_tiered: bool         # 是否阶梯教室
    row_id: int             # 表格行号


@dataclass
class ClassroomOccupancy:
    """教室占用情况数据类"""
    classroom_code: str     # 教室代码
    weekday: int           # 星期几 (1-7)
    period: int            # 节次
    reason: str            # 占用原因 ("排"=排课，"借"=借用，"考"=考试等)


@dataclass
class ClassroomAvailability:
    """教室可用性查询结果数据类"""
    academic_year: str      # 学年，如"2024-2025"
    semester: str           # 学期，如"2"
    building_code: str      # 教学楼代码
    week_mask: str          # 周次掩码
    classrooms: List[ClassroomInfo]           # 教室列表
    occupancies: List[ClassroomOccupancy]     # 占用情况列表
    query_time: str         # 查询时间戳


@dataclass
class SemesterFirstDay:
    """学期第一天信息数据类"""
    academic_year: str      # 学年，如"2024-2025"
    semester_code: str      # 学期代码，如"2"
    semester_full_code: str # 完整学期编码，如"2024-20252"
    first_day: datetime     # 学期第一天（第 0 周第一天）
    first_day_str: str      # 学期第一天字符串，如"2025-02-17"


@dataclass
class WeekdayInfo:
    """周次和星期信息数据类"""
    week_number: int        # 周次（从 0 开始）
    weekday: int           # 星期几（1=周一，7=周日）
    weekday_name: str      # 星期几的中文名称
    date: datetime         # 具体日期
    date_str: str          # 日期字符串


class JWClient(JWLoginClient):
    """哈工大（深圳）教务系统客户端，提供各种教务系统功能接口"""
    
    # 基础 URL
    BASE_URL = "http://jw.hitsz.edu.cn"
    
    def __init__(self, username: str = None, password: str = None):
        """
        初始化教务系统客户端
        
        Args:
            username: 学号/工号
            password: 密码
        """
        super().__init__(username, password)
        # 缓存数据
        self._cached_data: Optional[Dict[str, Any]] = None
        self._data_loaded: bool = False
        # 缓存当前学期信息
        self._current_semester: Optional[CurrentSemester] = None
        self._current_semester_loaded: bool = False
        # 缓存教学楼信息
        self._teaching_buildings: Optional[List[TeachingBuilding]] = None
        self._teaching_buildings_loaded: bool = False
        # 缓存教室可用性查询结果
        self._classroom_availability_cache: Dict[str, ClassroomAvailability] = {}
        self._classroom_availability_cache_ttl: Dict[str, float] = {}  # 缓存过期时间
        self._cache_duration: int = 300  # 缓存 5 分钟
        # 缓存学期第一天信息
        self._semester_first_day_cache: Dict[str, SemesterFirstDay] = {}
        self._semester_first_day_cache_loaded: Dict[str, bool] = {}
        
    def _prepare_session(self):
        """
        准备会话，确保已登录
        
        Returns:
            已认证的会话对象
        """
        if not self.is_logged_in:
            self.login()
        return self.session
    
    def _get_default_headers(self) -> Dict[str, str]:
        """
        获取默认请求头
        
        Returns:
            包含默认头信息的字典
        """
        return {
            "accept": "application/json, text/javascript, */*; q=0.01",
            "accept-language": "zh-CN,zh;q=0.9",
            "cache-control": "no-cache",
            "content-type": "application/json",
            "pragma": "no-cache",
            "rolecode": "01",
            "x-requested-with": "XMLHttpRequest"
        }
    
    def _parse_grade(self, raw_grade: Dict[str, Any]) -> CourseGrade:
        """
        解析原始成绩数据为 CourseGrade 对象
        
        Args:
            raw_grade: 原始成绩数据
            
        Returns:
            CourseGrade 对象
        """
        # 安全地转换学分
        credit_raw = raw_grade.get('xf', 0)
        try:
            credit = float(credit_raw) if credit_raw is not None else 0.0
        except (ValueError, TypeError):
            credit = 0.0
        
        return CourseGrade(
            course_id=raw_grade.get('kcdm', ''),              # 课程代码
            course_name=raw_grade.get('kcmc', ''),            # 课程名称
            course_name_en=raw_grade.get('kcmc_en', ''),      # 课程英文名称
            credit=credit,                                    # 学分
            semester=raw_grade.get('xnxq', ''),               # 学期编码
            semester_display=raw_grade.get('xnxqmc', ''),     # 学期显示名称
            score=raw_grade.get('zzcj', ''),                  # 总成绩
            score_raw=raw_grade.get('zzzscj', ''),            # 原始分数
            exam_type=raw_grade.get('khfs', ''),              # 考核方式
            course_type=raw_grade.get('kcxz', ''),            # 课程性质 (必修/选修)
            course_category=raw_grade.get('kclb', ''),        # 课程类别
            department=raw_grade.get('yxmc', ''),             # 开课院系
            is_pass=raw_grade.get('sfjg') == '0',             # 是否及格
            is_restudy=raw_grade.get('sfyfx') == '1',         # 是否重修
            rank=raw_grade.get('pm', '0'),                    # 排名
            total_students=raw_grade.get('zrs', '0')          # 总人数
        )
    
    def _parse_semester(self, raw_semester: Dict[str, Any]) -> SemesterInfo:
        """
        解析原始学期数据为 SemesterInfo 对象
        
        Args:
            raw_semester: 原始学期数据
            
        Returns:
            SemesterInfo 对象
        """
        return SemesterInfo(
            academic_year=raw_semester.get('xn', ''),         # 学年
            semester_code=raw_semester.get('xq', ''),         # 学期代码
            year_name=raw_semester.get('xnmc', ''),           # 年份名称
            semester_name=raw_semester.get('xqmc', ''),       # 学期名称
            year_name_en=raw_semester.get('xnmc_en', ''),     # 年份英文名称
            semester_name_en=raw_semester.get('xqmc_en', ''), # 学期英文名称
        )
    
    def _parse_current_semester(self, raw_data: Dict[str, Any]) -> CurrentSemester:
        """
        解析当前学年学期数据为 CurrentSemester 对象
        
        Args:
            raw_data: 原始当前学期数据
            
        Returns:
            CurrentSemester 对象
        """
        return CurrentSemester(
            academic_year=raw_data.get('XN', ''),        # 学年
            semester_full_code=raw_data.get('XNXQ', ''), # 完整学期编码
            semester_code=raw_data.get('XQ', '')         # 学期代码
        )
    
    def _parse_teaching_building(self, raw_building: Dict[str, Any]) -> TeachingBuilding:
        """
        解析教学楼数据为 TeachingBuilding 对象
        
        Args:
            raw_building: 原始教学楼数据
            
        Returns:
            TeachingBuilding 对象
        """
        return TeachingBuilding(
            name=raw_building.get('MC', ''),           # 教学楼名称
            code=raw_building.get('DM', ''),           # 教学楼代码
            name_en=raw_building.get('MC_EN')          # 教学楼英文名称
        )
    
    def _parse_classroom_info(self, raw_classroom: Dict[str, Any]) -> ClassroomInfo:
        """
        解析教室信息数据为 ClassroomInfo 对象
        
        Args:
            raw_classroom: 原始教室数据
            
        Returns:
            ClassroomInfo 对象
        """
        # 安全地转换座位数
        seats_raw = raw_classroom.get('ZWS', 0)
        seats = int(seats_raw) if seats_raw is not None and str(seats_raw).isdigit() else 0
        
        # 安全地转换行号
        row_id_raw = raw_classroom.get('ROW_ID', 0)
        row_id = int(row_id_raw) if row_id_raw is not None and str(row_id_raw).isdigit() else 0
        
        return ClassroomInfo(
            name=raw_classroom.get('MC', ''),                    # 教室名称
            code=raw_classroom.get('DM', ''),                    # 教室代码
            name_en=raw_classroom.get('MC_EN', ''),              # 教室英文名称
            seats=seats,                                         # 座位数
            is_available=raw_classroom.get('SFKJ') == '1',       # 是否可借用
            is_movable_seats=raw_classroom.get('ZYSFKYD') == '1', # 座椅是否可移动
            is_tiered=raw_classroom.get('SFJTJS') == '1',        # 是否阶梯教室
            row_id=row_id                                        # 表格行号
        )
    
    def _parse_classroom_occupancy(self, raw_occupancy: Dict[str, Any]) -> ClassroomOccupancy:
        """
        解析教室占用情况数据为 ClassroomOccupancy 对象
        
        Args:
            raw_occupancy: 原始占用情况数据
            
        Returns:
            ClassroomOccupancy 对象
        """
        # 安全地转换星期几
        weekday_raw = raw_occupancy.get('XQJ', 0)
        weekday = int(weekday_raw) if weekday_raw is not None and str(weekday_raw).isdigit() else 0
        
        # 安全地转换节次
        period_raw = raw_occupancy.get('XJ', 0)
        period = int(period_raw) if period_raw is not None and str(period_raw).isdigit() else 0
        
        return ClassroomOccupancy(
            classroom_code=raw_occupancy.get('CDDM', ''),        # 教室代码
            weekday=weekday,                                     # 星期几
            period=period,                                       # 节次
            reason=raw_occupancy.get('PKBJ', '')                 # 占用原因
        )
    
    def _load_data_if_needed(self, force_reload: bool = False):
        """
        如果需要的话加载数据到缓存
        
        Args:
            force_reload: 是否强制重新加载数据
        """
        if not self._data_loaded or force_reload:
            self._cached_data = self._fetch_all_data()
            self._data_loaded = True
    
    def _fetch_all_data(self) -> Dict[str, Any]:
        """
        从服务器获取所有数据（成绩和 GPA 信息）
        
        Returns:
            包含成绩列表和 GPA 信息的字典
        """
        # 获取成绩数据
        result = self._get_all_grades_raw()
        
        grades = []
        if (result and 'content' in result and 
            result['content'] is not None and 'list' in result['content'] and 
            isinstance(result['content']['list'], list)):
            
            raw_grades = result['content']['list']
            for raw_grade in raw_grades:
                try:
                    grade = self._parse_grade(raw_grade)
                    grades.append(grade)
                except Exception as e:
                    print(f"解析成绩数据失败：{e}")
        else:
            print(f"获取成绩数据失败或数据格式异常：{result}")
        
        response = {
            "grades": grades
        }
        
        # 获取 GPA 信息
        try:
            response["gpa_info"] = self._get_official_gpa()
        except Exception as e:
            print(f"获取 GPA 信息失败：{e}")
            response["gpa_info"] = None
                
        return response
    
    def query_grades(self, page: int = 1, page_size: int = 100) -> Dict[str, Any]:
        """
        查询个人成绩原始数据
        
        Args:
            page: 当前页码
            page_size: 每页条数
            
        Returns:
            成绩查询结果原始数据
        """
        session = self._prepare_session()
        
        # 构建请求参数 (根据网站实际参数设置)
        payload = {
            "xn": None,
            "xq": None,
            "kcmc": None,
            "cxbj": "-1",
            "pylx": "1",
            "current": page,
            "pageSize": page_size,
            "sffx": None
        }
        
        # 发送请求
        url = f"{self.BASE_URL}/cjgl/grcjcx/grcjcx"
        referer = f"{self.BASE_URL}/cjgl/grcjcx/go/1"
        
        headers = self._get_default_headers()
        headers["referer"] = referer
        
        try:
            response = session.post(
                url,
                headers=headers,
                data=json.dumps(payload)
            )
            
            # 检查响应
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"查询成绩失败：{e}")
            return {"content": {"list": [], "total": 0}}
    
    def _get_official_gpa(self) -> GPAInfo:
        """
        获取官方 GPA 信息（内部方法）
        
        Returns:
            GPA 信息对象
        """
        session = self._prepare_session()
        
        url = f"{self.BASE_URL}/cjgl/grcjcx/getgpa"
        referer = f"{self.BASE_URL}/cjgl/grcjcx/go/1"
        
        headers = self._get_default_headers()
        headers["accept"] = "*/*"
        headers["referer"] = referer
        headers["content-type"] = "application/x-www-form-urlencoded; charset=UTF-8"
        
        response = session.post(url, headers=headers)
        response.raise_for_status()
        
        data = response.json()
        
        # 计算排名百分比
        rank_percentage = 0.0
        rank_raw = data.get('PM', 0)
        total_raw = data.get('ZRS', 0)
        try:
            rank_val = float(rank_raw) if rank_raw is not None else 0
            total_val = float(total_raw) if total_raw is not None else 0
            if total_val > 0:
                rank_percentage = round(rank_val / total_val * 100, 2)
        except (ValueError, TypeError, ZeroDivisionError):
            rank_percentage = 0.0
        
        # 安全地转换数值类型
        def safe_float(value, default=0.0):
            try:
                return float(value) if value is not None else default
            except (ValueError, TypeError):
                return default
        
        def safe_int(value, default=0):
            try:
                return int(value) if value is not None else default
            except (ValueError, TypeError):
                return default
        
        return GPAInfo(
            gpa=safe_float(data.get('GPA', 0)),                # 核心课 GPA
            all_course_gpa=safe_float(data.get('GPA_QBJQKC', 0)),  # 全部课程 GPA
            avg_score=safe_float(data.get('PJXFJ', 0)),        # 核心课平均学分绩
            all_course_avg_score=safe_float(data.get('QBKCPJXFJ', 0)),  # 全部课程平均学分绩
            rank=safe_int(data.get('PM', 0)),                  # 排名
            total_students=safe_int(data.get('ZRS', 0)),       # 总人数
            rank_percentage=rank_percentage,                   # 排名百分比
            passed_courses=safe_int(data.get('TGKC', 0)),      # 通过课程数
            total_credits=safe_float(data.get('HDXF', 0))      # 获得学分
        )
    
    def _get_current_semester_raw(self) -> CurrentSemester:
        """
        获取当前学年学期信息（内部方法）
        
        Returns:
            CurrentSemester 对象
        """
        session = self._prepare_session()
        
        url = f"{self.BASE_URL}/kbfbsz/querydqxnxq"
        referer = f"{self.BASE_URL}/cdkb/querycdzy"
        
        headers = self._get_default_headers()
        headers["accept"] = "*/*"
        headers["referer"] = referer
        del headers["content-type"]  # 这个接口不需要 content-type
        
        response = session.post(url, headers=headers)
        response.raise_for_status()
        
        data = response.json()
        return self._parse_current_semester(data)
    
    def _get_teaching_buildings_raw(self) -> List[TeachingBuilding]:
        """
        获取教学楼列表信息（内部方法）
        
        Returns:
            教学楼列表
        """
        session = self._prepare_session()
        
        url = f"{self.BASE_URL}/pksd/queryjxlList"
        referer = f"{self.BASE_URL}/cdkb/querycdzy"
        
        headers = self._get_default_headers()
        headers["accept"] = "*/*"
        headers["referer"] = referer
        del headers["content-type"]  # 这个接口不需要 content-type
        
        try:
            response = session.post(url, headers=headers)
            response.raise_for_status()
            
            data = response.json()
            buildings = []
            
            if isinstance(data, list):
                for raw_building in data:
                    try:
                        building = self._parse_teaching_building(raw_building)
                        buildings.append(building)
                    except Exception as e:
                        print(f"解析教学楼数据失败：{e}")
            else:
                print(f"教学楼数据格式异常：{data}")
                
            return buildings
            
        except Exception as e:
            print(f"获取教学楼列表失败：{e}")
            return []
    
    def _get_classrooms_raw(self, academic_year: str, semester: str, building_code: str, 
                           week_mask: str, week_numbers: str = "", page: int = 1, 
                           page_size: int = 100) -> Dict[str, Any]:
        """
        获取教室列表原始数据（内部方法）
        
        Args:
            academic_year: 学年，如"2024-2025"
            semester: 学期，如"2"
            building_code: 教学楼代码
            week_mask: 周次掩码，如"0000010000000000000000000000000000"
            week_numbers: 具体查询周数，如"3-5,8"，可为空
            page: 页码
            page_size: 每页大小
            
        Returns:
            教室列表原始数据
        """
        session = self._prepare_session()
        
        url = f"{self.BASE_URL}/cdkb/querycdzyleftzhou"
        referer = f"{self.BASE_URL}/cdkb/querycdzy"
        
        headers = self._get_default_headers()
        headers["referer"] = referer
        headers["content-type"] = "application/x-www-form-urlencoded; charset=UTF-8"
        
        # 构建请求参数
        payload = {
            "pxn": academic_year,
            "pxq": semester,
            "dmmc": "",
            "xiaoqu": "",
            "jxl": building_code,
            "cdlb": "",
            "zc": week_mask,
            "wpksfxs": "1",  # 必须为 1，否则没课的教室不会被查询到
            "qsjsz": week_numbers,
            "kjs": "0",
            "xsbkycd": "0",
            "zws": "",
            "pageNum": str(page),
            "pageSize": str(page_size)
        }
        
        # 将参数转换为 URL 编码格式
        body_parts = []
        for key, value in payload.items():
            body_parts.append(f"{key}={value}")
        body = "&".join(body_parts)
        
        try:
            response = session.post(url, headers=headers, data=body)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"获取教室列表失败：{e}")
            return {"total": 0, "list": []}
    
    def _get_classroom_occupancy_raw(self, academic_year: str, semester: str, building_code: str,
                                   week_mask: str, week_numbers: str = "") -> List[Dict[str, Any]]:
        """
        获取教室占用情况原始数据（内部方法）
        
        Args:
            academic_year: 学年，如"2024-2025"
            semester: 学期，如"2"
            building_code: 教学楼代码
            week_mask: 周次掩码
            week_numbers: 具体查询周数，可为空
            
        Returns:
            教室占用情况原始数据列表
        """
        session = self._prepare_session()
        
        url = f"{self.BASE_URL}/cdkb/querycdzyrightzhou"
        referer = f"{self.BASE_URL}/cdkb/querycdzy"
        
        headers = self._get_default_headers()
        headers["accept"] = "*/*"
        headers["referer"] = referer
        headers["content-type"] = "application/x-www-form-urlencoded; charset=UTF-8"
        
        # 构建请求参数
        payload = {
            "pxn": academic_year,
            "pxq": semester,
            "dmmc": "",
            "xiaoqu": "",
            "jxl": building_code,
            "cdlb": "",
            "zc": week_mask,
            "wpksfxs": "1",
            "qsjsz": week_numbers,
            "kjs": "0",
            "xsbkycd": "0",
            "zws": "",
            "pageNum": "1",
            "pageSize": "1000"  # 设置较大值获取所有占用情况
        }
        
        # 将参数转换为 URL 编码格式
        body_parts = []
        for key, value in payload.items():
            body_parts.append(f"{key}={value}")
        body = "&".join(body_parts)
        
        try:
            response = session.post(url, headers=headers, data=body)
            response.raise_for_status()
            data = response.json()
            
            # 这个接口直接返回数组
            if isinstance(data, list):
                return data
            else:
                print(f"教室占用情况数据格式异常：{data}")
                return []
                
        except Exception as e:
            print(f"获取教室占用情况失败：{e}")
            return []
    
    def _get_all_grades_raw(self) -> Dict[str, Any]:
        """
        获取所有学期的成绩原始数据，自动处理分页（内部方法）
        
        Returns:
            所有成绩记录的原始数据
        """
        page = 1
        page_size = 100  # 较大的页面大小减少请求次数
        
        result = self.query_grades(page=page, page_size=page_size)
        
        # 检查是否需要处理分页
        if (result and 'content' in result and 
            result['content'] is not None and 'total' in result['content']):
            total = result['content']['total']
            
            # 如果总记录数大于页面大小，需要重新查询以获取所有数据
            if total > page_size:
                return self.query_grades(page=1, page_size=total)
                
        return result
    
    def _get_semester_first_day_raw(self, academic_year: str, semester: str) -> SemesterFirstDay:
        """
        获取学期第一天信息（内部方法）
        
        Args:
            academic_year: 学年，如"2024-2025"
            semester: 学期代码，如"2"
            
        Returns:
            学期第一天信息对象
        """
        session = self._prepare_session()
        
        url = f"{self.BASE_URL}/Xiaoli/queryMonthList"
        referer = f"{self.BASE_URL}/Xiaoli/query"
        
        headers = self._get_default_headers()
        headers["accept"] = "*/*"
        headers["referer"] = referer
        headers["content-type"] = "application/x-www-form-urlencoded; charset=UTF-8"
        
        # 构建请求参数
        payload = f"dm=&zyw=zh&xnxq=&pxn={academic_year}&pxq={semester}"
        
        try:
            response = session.post(url, headers=headers, data=payload)
            response.raise_for_status()
            
            data = response.json()
            
            # 从 xlList 中获取第一个元素的 RQ 字段
            if 'xlList' in data and isinstance(data['xlList'], list) and len(data['xlList']) > 0:
                first_item = data['xlList'][0]
                first_day_str = first_item.get('RQ', '')
                semester_full_code = first_item.get('XNXQ', f"{academic_year}{semester}")
                
                if first_day_str:
                    # 解析日期字符串
                    first_day = datetime.strptime(first_day_str, '%Y-%m-%d')
                    
                    return SemesterFirstDay(
                        academic_year=academic_year,
                        semester_code=semester,
                        semester_full_code=semester_full_code,
                        first_day=first_day,
                        first_day_str=first_day_str
                    )
                else:
                    raise ValueError(f"无法从响应中获取学期第一天信息：{first_item}")
            else:
                raise ValueError(f"响应数据格式异常，xlList 为空或不存在：{data}")
                
        except Exception as e:
            print(f"获取学期第一天信息失败：{e}")
            raise
    
    def get_all_grades(self, force_reload: bool = False) -> Dict[str, Any]:
        """
        获取所有学期的成绩和 GPA 信息（基础数据源）
        
        Args:
            force_reload: 是否强制重新从服务器加载数据
            
        Returns:
            包含成绩列表和 GPA 信息的字典
        """
        self._load_data_if_needed(force_reload)
        return self._cached_data.copy() if self._cached_data else {"grades": [], "gpa_info": None}
    
    def get_gpa_info(self) -> Optional[GPAInfo]:
        """
        获取 GPA 信息（基于缓存数据）
        
        Returns:
            GPA 信息对象，如果没有数据则返回 None
        """
        self._load_data_if_needed()
        return self._cached_data.get("gpa_info") if self._cached_data else None
    
    def get_semester_list(self) -> List[Dict[str, str]]:
        """
        获取已有成绩的学期列表（基于缓存数据）
        
        Returns:
            学期列表，每个学期包含编码和显示名称
        """
        self._load_data_if_needed()
        grades = self._cached_data.get("grades", []) if self._cached_data else []
        
        # 提取不重复的学期信息
        semesters = {}
        for grade in grades:
            if grade.semester not in semesters:
                semesters[grade.semester] = grade.semester_display
        
        # 转换为列表并排序
        semester_list = [
            {"code": code, "name": name} 
            for code, name in semesters.items()
        ]
        semester_list.sort(key=lambda x: x["code"], reverse=True)
        
        return semester_list
    
    def get_grades_by_semester(self, semester_code: str) -> List[CourseGrade]:
        """
        获取指定学期的成绩（基于缓存数据）
        
        Args:
            semester_code: 学期编码，如"2022-20231"
            
        Returns:
            指定学期的成绩列表
        """
        self._load_data_if_needed()
        all_grades = self._cached_data.get("grades", []) if self._cached_data else []
        return [grade for grade in all_grades if grade.semester == semester_code]
    
    def export_grades_to_csv(self, filename: str = "grades.csv") -> str:
        """
        导出成绩为 CSV 文件（基于缓存数据）
        
        Args:
            filename: 导出的文件名
            
        Returns:
            导出文件的完整路径
        """
        self._load_data_if_needed()
        data = self._cached_data if self._cached_data else {"grades": [], "gpa_info": None}
        grades = data["grades"]
        gpa_info = data.get("gpa_info")
        
        # 确保文件扩展名为.csv
        if not filename.endswith('.csv'):
            filename += '.csv'
        
        filepath = os.path.abspath(filename)
        
        # 写入 CSV 文件
        with open(filepath, 'w', newline='', encoding='utf-8-sig') as csvfile:
            writer = csv.writer(csvfile)
            
            # 写入 GPA 信息
            if gpa_info:
                writer.writerow(['GPA 统计信息'])
                writer.writerow(['核心课 GPA', '全部课程 GPA', '核心课平均学分绩', '全部课程平均学分绩', '排名', '总人数', '排名百分比', '通过课程数', '获得学分'])
                writer.writerow([
                    gpa_info.gpa, 
                    gpa_info.all_course_gpa,
                    gpa_info.avg_score,
                    gpa_info.all_course_avg_score,
                    gpa_info.rank,
                    gpa_info.total_students,
                    f"{gpa_info.rank_percentage}%",
                    gpa_info.passed_courses,
                    gpa_info.total_credits
                ])
                writer.writerow([])  # 空行分隔
            
            # 写入成绩表头
            writer.writerow([
                '学期', '课程代码', '课程名称', '课程英文名称', '学分', 
                '成绩', '原始分数', '考核方式', '课程类型', '课程类别', 
                '开课院系', '是否及格', '是否重修', '排名', '总人数'
            ])
            
            # 写入成绩数据
            for grade in grades:
                writer.writerow([
                    grade.semester_display,
                    grade.course_id,
                    grade.course_name,
                    grade.course_name_en,
                    grade.credit,
                    grade.score,
                    grade.score_raw,
                    grade.exam_type,
                    grade.course_type,
                    grade.course_category,
                    grade.department,
                    '是' if grade.is_pass else '否',
                    '是' if grade.is_restudy else '否',
                    grade.rank,
                    grade.total_students
                ])
        
        return filepath
    
    def get_current_semester(self, force_reload: bool = False) -> CurrentSemester:
        """
        获取当前学年学期信息（带缓存）
        
        Args:
            force_reload: 是否强制重新从服务器加载数据
            
        Returns:
            当前学期信息对象
        """
        if not self._current_semester_loaded or force_reload:
            self._current_semester = self._get_current_semester_raw()
            self._current_semester_loaded = True
        
        return self._current_semester
    
    def get_teaching_buildings(self, force_reload: bool = False) -> List[TeachingBuilding]:
        """
        获取教学楼列表（带缓存）
        
        Args:
            force_reload: 是否强制重新从服务器加载数据
            
        Returns:
            教学楼列表
        """
        if not self._teaching_buildings_loaded or force_reload:
            self._teaching_buildings = self._get_teaching_buildings_raw()
            self._teaching_buildings_loaded = True
        
        return self._teaching_buildings.copy() if self._teaching_buildings else []
    
    def get_all_semesters(self) -> List[SemesterInfo]:
        """
        获取所有学年学期列表
        
        Returns:
            学期信息列表
        """
        session = self._prepare_session()
        
        url = f"{self.BASE_URL}/component/queryXnxqCdjy"
        referer = f"{self.BASE_URL}/cdkb/querycdzy"
        
        headers = self._get_default_headers()
        headers["accept"] = "*/*"
        headers["referer"] = referer
        headers["content-type"] = "application/x-www-form-urlencoded; charset=UTF-8"
        
        # 发送请求
        response = session.post(
            url,
            headers=headers,
            data="data="
        )
        
        response.raise_for_status()
        result = response.json()
        
        semesters = []
        if result.get('code') == 200 and 'content' in result:
            raw_semesters = result['content']
            if isinstance(raw_semesters, list):
                for raw_semester in raw_semesters:
                    try:
                        semester = self._parse_semester(raw_semester)
                        semesters.append(semester)
                    except Exception as e:
                        print(f"解析学期数据失败：{e}")
        
        return semesters
    
    def get_semester_first_day(self, academic_year: str = None, semester: str = None, 
                              force_reload: bool = False) -> SemesterFirstDay:
        """
        获取学期第一天信息（带缓存）
        
        Args:
            academic_year: 学年，如"2024-2025"，为 None 时使用当前学年
            semester: 学期代码，如"2"，为 None 时使用当前学期
            force_reload: 是否强制重新从服务器加载数据
            
        Returns:
            学期第一天信息对象
        """
        # 参数处理
        if academic_year is None or semester is None:
            current_semester = self.get_current_semester()
            if academic_year is None:
                academic_year = current_semester.academic_year
            if semester is None:
                semester = current_semester.semester_code
        
        cache_key = f"{academic_year}_{semester}"
        
        # 检查缓存
        if not force_reload and cache_key in self._semester_first_day_cache_loaded and self._semester_first_day_cache_loaded[cache_key]:
            return self._semester_first_day_cache[cache_key]
        
        # 从服务器获取数据
        semester_first_day = self._get_semester_first_day_raw(academic_year, semester)
        
        # 更新缓存
        self._semester_first_day_cache[cache_key] = semester_first_day
        self._semester_first_day_cache_loaded[cache_key] = True
        
        return semester_first_day
    
    def calculate_week_and_weekday(self, target_date: Union[datetime, str], 
                                 academic_year: str = None, semester: str = None) -> WeekdayInfo:
        """
        根据日期计算当前是第几周星期几
        
        Args:
            target_date: 目标日期，可以是 datetime 对象或字符串（格式：YYYY-MM-DD）
            academic_year: 学年，如"2024-2025"，为 None 时使用当前学年
            semester: 学期代码，如"2"，为 None 时使用当前学期
            
        Returns:
            周次和星期信息对象
        """
        # 处理日期参数
        if isinstance(target_date, str):
            target_date = datetime.strptime(target_date, '%Y-%m-%d')
        
        # 获取学期第一天
        semester_first_day = self.get_semester_first_day(academic_year, semester)
        
        # 计算日期差
        date_diff = target_date - semester_first_day.first_day
        days_diff = date_diff.days
        
        # 计算周次（第 0 周开始）
        week_number = days_diff // 7
        
        # 计算星期几（1=周一，7=周日）
        # Python 的 weekday() 返回 0-6（0=周一），需要转换为 1-7
        weekday = target_date.weekday() + 1
        
        # 星期几的中文名称
        weekday_names = ["", "周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        weekday_name = weekday_names[weekday] if 1 <= weekday <= 7 else f"星期{weekday}"
        
        return WeekdayInfo(
            week_number=week_number,
            weekday=weekday,
            weekday_name=weekday_name,
            date=target_date,
            date_str=target_date.strftime('%Y-%m-%d')
        )
    
    def _generate_cache_key(self, academic_year: str, semester: str, building_code: str, week_mask: str) -> str:
        """
        生成缓存键
        
        Args:
            academic_year: 学年
            semester: 学期
            building_code: 教学楼代码
            week_mask: 周次掩码
            
        Returns:
            缓存键字符串
        """
        return f"{academic_year}_{semester}_{building_code}_{week_mask}"
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """
        检查缓存是否有效
        
        Args:
            cache_key: 缓存键
            
        Returns:
            缓存是否有效
        """
        import time
        if cache_key not in self._classroom_availability_cache_ttl:
            return False
        return time.time() < self._classroom_availability_cache_ttl[cache_key]
    
    def generate_week_mask(self, week_numbers: List[int]) -> str:
        """
        生成周次掩码
        
        Args:
            week_numbers: 周次列表，如 [1, 3, 5]
            
        Returns:
            周次掩码字符串，如"0101010000000000000000000000000000"
        """
        # 创建 34 位的掩码（通常一学期最多 34 周）
        mask = ['0'] * 34
        
        for week in week_numbers:
            if 1 <= week <= 34:
                mask[week] = '1'
        
        return ''.join(mask)
    
    def parse_week_numbers(self, week_string: str) -> List[int]:
        """
        解析周次字符串为周次列表
        
        Args:
            week_string: 周次字符串，如"3-5,8,10-12"
            
        Returns:
            周次列表，如 [3, 4, 5, 8, 10, 11, 12]
        """
        weeks = []
        if not week_string.strip():
            return weeks
            
        parts = week_string.split(',')
        for part in parts:
            part = part.strip()
            if '-' in part:
                # 处理范围，如"3-5"
                start, end = part.split('-')
                start, end = int(start.strip()), int(end.strip())
                weeks.extend(range(start, end + 1))
            else:
                # 处理单个周次
                weeks.append(int(part))
        
        return sorted(list(set(weeks)))  # 去重并排序
    
    def query_classroom_availability(self, academic_year: str = None, semester: str = None,
                                   building_code: str = None, week_numbers: List[int] = None,
                                   week_string: str = None, use_cache: bool = True) -> ClassroomAvailability:
        """
        查询教室可用性
        
        Args:
            academic_year: 学年，如"2024-2025"，为 None 时使用当前学年
            semester: 学期，如"2"，为 None 时使用当前学期
            building_code: 教学楼代码，必须提供
            week_numbers: 周次列表，如 [1, 3, 5]
            week_string: 周次字符串，如"3-5,8"，与 week_numbers 二选一
            use_cache: 是否使用缓存
            
        Returns:
            教室可用性查询结果
        """
        import time
        
        # 参数处理
        if academic_year is None or semester is None:
            current_semester = self.get_current_semester()
            if academic_year is None:
                academic_year = current_semester.academic_year
            if semester is None:
                semester = current_semester.semester_code
        
        if building_code is None:
            raise ValueError("building_code 参数不能为空")
        
        # 处理周次参数
        if week_numbers is None and week_string is None:
            raise ValueError("week_numbers 和 week_string 至少需要提供一个")
        
        if week_numbers is None:
            week_numbers = self.parse_week_numbers(week_string)
        
        if not week_numbers:
            raise ValueError("周次列表不能为空")
        
        week_mask = self.generate_week_mask(week_numbers)
        week_numbers_str = ','.join(map(str, week_numbers))
        
        # 检查缓存
        cache_key = self._generate_cache_key(academic_year, semester, building_code, week_mask)
        if use_cache and self._is_cache_valid(cache_key):
            return self._classroom_availability_cache[cache_key]
        
        # 获取教室列表数据
        classrooms_data = self._get_classrooms_raw(
            academic_year, semester, building_code, week_mask, week_numbers_str
        )
        
        # 解析教室信息
        classrooms = []
        if classrooms_data.get('list'):
            for raw_classroom in classrooms_data['list']:
                try:
                    classroom = self._parse_classroom_info(raw_classroom)
                    classrooms.append(classroom)
                except Exception as e:
                    print(f"解析教室信息失败：{e}")
        
        # 获取教室占用情况数据
        occupancy_data = self._get_classroom_occupancy_raw(
            academic_year, semester, building_code, week_mask, week_numbers_str
        )
        
        # 解析占用情况
        occupancies = []
        for raw_occupancy in occupancy_data:
            try:
                occupancy = self._parse_classroom_occupancy(raw_occupancy)
                occupancies.append(occupancy)
            except Exception as e:
                print(f"解析教室占用情况失败：{e}")
        
        # 创建结果对象
        result = ClassroomAvailability(
            academic_year=academic_year,
            semester=semester,
            building_code=building_code,
            week_mask=week_mask,
            classrooms=classrooms,
            occupancies=occupancies,
            query_time=str(int(time.time()))
        )
        
        # 更新缓存
        if use_cache:
            self._classroom_availability_cache[cache_key] = result
            self._classroom_availability_cache_ttl[cache_key] = time.time() + self._cache_duration
        
        return result
    
    def get_available_classrooms(self, academic_year: str = None, semester: str = None,
                               building_code: str = None, week_numbers: List[int] = None,
                               week_string: str = None, weekday: int = None, period: int = None,
                               min_seats: int = None, use_cache: bool = True) -> List[ClassroomInfo]:
        """
        获取可用教室列表（过滤后的结果）
        
        Args:
            academic_year: 学年
            semester: 学期
            building_code: 教学楼代码
            week_numbers: 周次列表
            week_string: 周次字符串
            weekday: 星期几 (1-7)，为 None 时不过滤
            period: 节次，为 None 时不过滤
            min_seats: 最少座位数，为 None 时不过滤
            use_cache: 是否使用缓存
            
        Returns:
            可用教室列表
        """
        # 获取完整的查询结果
        availability = self.query_classroom_availability(
            academic_year, semester, building_code, week_numbers, week_string, use_cache
        )
        
        # 获取被占用的教室代码集合
        occupied_classrooms = set()
        for occupancy in availability.occupancies:
            # 如果指定了星期几和节次，只考虑匹配的占用情况
            if weekday is not None and occupancy.weekday != weekday:
                continue
            if period is not None and occupancy.period != period:
                continue
            occupied_classrooms.add(occupancy.classroom_code)
        
        # 过滤可用教室
        available_classrooms = []
        for classroom in availability.classrooms:
            # 检查是否被占用
            if classroom.code in occupied_classrooms:
                continue
            
            # 检查是否可借用
            if not classroom.is_available:
                continue
            
            # 检查座位数要求
            if min_seats is not None and classroom.seats < min_seats:
                continue
            
            available_classrooms.append(classroom)
        
        # 按座位数排序
        available_classrooms.sort(key=lambda x: x.seats, reverse=True)
        
        return available_classrooms
    
    def refresh_data(self):
        """
        刷新缓存数据，强制从服务器重新获取
        """
        self._cached_data = None
        self._data_loaded = False
        self._current_semester = None
        self._current_semester_loaded = False
        self._teaching_buildings = None
        self._teaching_buildings_loaded = False
        # 清理教室可用性缓存
        self._classroom_availability_cache.clear()
        self._classroom_availability_cache_ttl.clear()
        # 清理学期第一天缓存
        self._semester_first_day_cache.clear()
        self._semester_first_day_cache_loaded.clear()
        self._load_data_if_needed(force_reload=True)


# 使用示例
if __name__ == "__main__":
    # 初始化客户端
    client = JWClient(username="210110703", password="@96236007Sc")
    
    # 查询所有成绩和 GPA 信息（第一次会从服务器获取并缓存）
    result = client.get_all_grades()
    grades = result["grades"]
    gpa_info = result.get("gpa_info")
    
    print(f"共找到 {len(grades)} 门课程成绩")
    
    # 打印 GPA 信息（使用缓存数据）
    if gpa_info:
        print(f"核心课 GPA: {gpa_info.gpa}, 平均学分绩：{gpa_info.avg_score}")
        print(f"排名：{gpa_info.rank}/{gpa_info.total_students} (前 {gpa_info.rank_percentage}%)")
        print(f"获得学分：{gpa_info.total_credits}, 通过课程数：{gpa_info.passed_courses}")
    
    # 获取学期列表（使用缓存数据）
    semesters = client.get_semester_list()
    print(f"共有 {len(semesters)} 个学期")
    
    # 获取当前学年学期信息（带缓存）
    current_semester = client.get_current_semester()
    print(f"当前学期：{current_semester.academic_year} 第{current_semester.semester_code}学期")
    print(f"完整编码：{current_semester.semester_full_code}")
    
    # 获取教学楼列表（带缓存）
    buildings = client.get_teaching_buildings()
    print(f"共有 {len(buildings)} 个教学楼")
    for building in buildings[:5]:  # 显示前 5 个教学楼
        en_name = f" ({building.name_en})" if building.name_en else ""
        print(f"  {building.name} (代码：{building.code}){en_name}")
    
    # 获取所有学年学期列表（从服务器获取）
    all_semesters = client.get_all_semesters()
    print(f"系统中共有 {len(all_semesters)} 个学期")
    for semester in all_semesters[:3]:  # 显示前 3 个学期
        print(f"  {semester.academic_year} {semester.semester_name} ({semester.semester_name_en})")
    
    # 导出成绩为 CSV（使用缓存数据）
    csv_path = client.export_grades_to_csv("我的成绩单.csv")
    print(f"成绩单已导出到：{csv_path}")
    
    print("\n" + "="*50)
    print("学期日期计算示例")
    print("="*50)
    
    # 获取当前学期第一天
    try:
        semester_first_day = client.get_semester_first_day()
        print(f"当前学期第一天：{semester_first_day.first_day_str}")
        print(f"学期编码：{semester_first_day.semester_full_code}")
        
        # 计算今天是第几周星期几
        from datetime import datetime
        today = datetime.now()
        weekday_info = client.calculate_week_and_weekday(today)
        print(f"今天 ({weekday_info.date_str}) 是第 {weekday_info.week_number} 周 {weekday_info.weekday_name}")
        
        # 计算指定日期是第几周星期几
        test_date = "2025-03-10"  # 示例日期
        weekday_info2 = client.calculate_week_and_weekday(test_date)
        print(f"{test_date} 是第 {weekday_info2.week_number} 周 {weekday_info2.weekday_name}")
        
    except Exception as e:
        print(f"学期日期计算失败：{e}")
    
    print("\n" + "="*50)
    print("教室可用性查询示例")
    print("="*50)
    
    # 教室可用性查询示例
    try:
        # 查询 T5 楼第 16 周的教室可用性
        availability = client.query_classroom_availability(
            building_code="17",  # T5 楼的代码
            week_string="16"     # 第 16 周
        )
        
        print(f"查询结果：{availability.academic_year} 第{availability.semester}学期")
        print(f"教学楼代码：{availability.building_code}")
        print(f"共找到 {len(availability.classrooms)} 间教室")
        print(f"共有 {len(availability.occupancies)} 个占用记录")
        
        # 显示前 5 间教室信息
        print("\n教室列表（前 5 间）:")
        for classroom in availability.classrooms[:5]:
            movable = "可移动" if classroom.is_movable_seats else "固定"
            tiered = "阶梯" if classroom.is_tiered else "平面"
            available = "可借" if classroom.is_available else "不可借"
            print(f"  {classroom.name}: {classroom.seats}座位，{movable}座椅，{tiered}教室，{available}")
        
        # 显示占用情况（前 10 个）
        print(f"\n占用情况（前 10 个）:")
        weekdays = ["", "周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        for occupancy in availability.occupancies[:10]:
            weekday_name = weekdays[occupancy.weekday] if 1 <= occupancy.weekday <= 7 else f"星期{occupancy.weekday}"
            print(f"  {occupancy.classroom_code}: {weekday_name} 第{occupancy.period}节 ({occupancy.reason})")
        
        # 查询周三第 3-4 节可用的教室（至少 50 个座位）
        available_classrooms = client.get_available_classrooms(
            building_code="17",
            week_string="16",
            weekday=3,      # 周三
            period=3,       # 第 3 节
            min_seats=50    # 至少 50 个座位
        )
        
        print(f"\n周三第 3 节可用教室（≥50 座位）: {len(available_classrooms)}间")
        for classroom in available_classrooms[:5]:
            print(f"  {classroom.name}: {classroom.seats}座位")
            
    except Exception as e:
        print(f"教室查询失败：{e}")
        print("请检查教学楼代码是否正确，或者网络连接是否正常") 