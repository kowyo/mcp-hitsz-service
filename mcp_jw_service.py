import json
import os
import sys
from dataclasses import asdict
from typing import Dict, List, Optional, Any, Union
from datetime import datetime

# 显示环境信息以便调试
print(f"Python version: {sys.version}", file=sys.stderr)
print(f"Current working directory: {os.getcwd()}", file=sys.stderr)
# 显示 python 路径
print(f"Python path: {sys.executable}", file=sys.stderr)
# 显示 which python
# print(f"Which python: {!which python}", file=sys.stderr)

# 加载环境变量
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("Successfully loaded .env file", file=sys.stderr)
except ImportError:
    print("Warning: python-dotenv not installed. Please install it: pip install python-dotenv", file=sys.stderr)
    print("Or manually set HITSZ_USERNAME and HITSZ_PASSWORD environment variables", file=sys.stderr)
except Exception as e:
    print(f"Warning: Could not load .env file: {e}", file=sys.stderr)

try:
    from mcp.server import FastMCP
    print("Successfully imported FastMCP", file=sys.stderr)
except ImportError as e:
    print(f"Error importing FastMCP: {e}", file=sys.stderr)
    print("Please install the mcp package: pip install mcp", file=sys.stderr)
    sys.exit(1)

try:
    from JWClient import (
        JWClient, CourseGrade, GPAInfo, SemesterInfo, CurrentSemester,
        TeachingBuilding, ClassroomInfo, ClassroomAvailability, 
        SemesterFirstDay, WeekdayInfo
    )
    print("Successfully imported JWClient", file=sys.stderr)
except ImportError as e:
    print(f"Error importing JWClient: {e}", file=sys.stderr)
    print("Make sure JWClient.py is in the current directory", file=sys.stderr)
    sys.exit(1)

# 初始化 FastMCP 服务器
print("Initializing FastMCP server...", file=sys.stderr)
app = FastMCP('hitsz-jw-service')
print("FastMCP server initialized", file=sys.stderr)

# 全局共享的 JWClient 实例
_client = None

def get_credentials() -> tuple[str, str]:
    """
    从环境变量获取登录凭据
    
    Returns:
        (username, password) 元组
        
    Raises:
        ValueError: 如果凭据未设置
    """
    username = os.getenv('HITSZ_USERNAME')
    password = os.getenv('HITSZ_PASSWORD')
    
    if not username or not password:
        raise ValueError(
            "请设置登录凭据！\n"
            "方法 1: 创建 .env 文件，内容如下：\n"
            "HITSZ_USERNAME=your_student_id\n"
            "HITSZ_PASSWORD=your_password\n\n"
            "方法 2: 设置环境变量：\n"
            "export HITSZ_USERNAME=your_student_id\n"
            "export HITSZ_PASSWORD=your_password"
        )
    
    return username, password

def get_client() -> JWClient:
    """获取或初始化 JWClient 实例"""
    global _client
    if _client is None:
        try:
            username, password = get_credentials()
            _client = JWClient(username=username, password=password)
            print(f"Created JWClient instance for user: {username}", file=sys.stderr)
        except Exception as e:
            print(f"Error creating JWClient: {e}", file=sys.stderr)
            raise
    return _client

def ensure_logged_in(client: JWClient) -> None:
    """确保客户端已登录"""
    if not client.is_logged_in:
        try:
            username, password = get_credentials()
            client.login(username, password)
            print("Auto-login successful", file=sys.stderr)
        except Exception as e:
            print(f"Auto-login failed: {e}", file=sys.stderr)
            raise


# ==================== 成绩相关工具 ====================

@app.tool()
async def get_all_grades(force_reload: bool = False) -> Dict[str, Any]:
    """
    获取所有课程成绩和 GPA 信息，这是获取成绩数据的主要入口
    
    Args:
        force_reload: 是否强制重新加载数据（默认使用缓存）
        
    Returns:
        包含所有成绩和 GPA 信息的完整数据
    """
    print(f"Fetching all grades (force_reload={force_reload})", file=sys.stderr)
    try:
        client = get_client()
        ensure_logged_in(client)
        
        result = client.get_all_grades(force_reload=force_reload)
        grades = result["grades"]
        
        print(f"Found {len(grades)} courses", file=sys.stderr)
        
        # 转换为字典格式以便 JSON 序列化
        grades_dict = [asdict(grade) for grade in grades]
        
        response = {
            "success": True,
            "grades": grades_dict,
            "total_courses": len(grades),
            "message": f"成功获取 {len(grades)} 门课程成绩"
        }
        
        # 添加 GPA 信息（如果有）
        if result.get("gpa_info"):
            response["gpa_info"] = asdict(result["gpa_info"])
            print("GPA info included", file=sys.stderr)
            
        return response
    except Exception as e:
        print(f"Error fetching grades: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        return {"success": False, "message": f"获取成绩失败：{str(e)}"}


@app.tool()
async def get_gpa_info() -> Dict[str, Any]:
    """
    获取 GPA 和排名信息
    
    Returns:
        包含 GPA、排名、平均分等详细信息
    """
    print("Fetching GPA info", file=sys.stderr)
    try:
        client = get_client()
        ensure_logged_in(client)
        
        gpa_info = client.get_gpa_info()
        if gpa_info is None:
            return {"success": False, "message": "未找到 GPA 信息"}
            
        print("GPA info fetched successfully", file=sys.stderr)
        return {
            "success": True,
            "gpa_info": asdict(gpa_info)
        }
    except Exception as e:
        print(f"Error fetching GPA info: {e}", file=sys.stderr)
        return {"success": False, "message": f"获取 GPA 信息失败：{str(e)}"}


@app.tool()
async def get_semester_list() -> Dict[str, Any]:
    """
    获取已有成绩的学期列表
    
    Returns:
        学期列表，包含学期代码和显示名称
    """
    print("Fetching semester list", file=sys.stderr)
    try:
        client = get_client()
        ensure_logged_in(client)
        
        semesters = client.get_semester_list()
        print(f"Found {len(semesters)} semesters", file=sys.stderr)
        return {
            "success": True,
            "semesters": semesters,
            "total_semesters": len(semesters)
        }
    except Exception as e:
        print(f"Error fetching semester list: {e}", file=sys.stderr)
        return {"success": False, "message": f"获取学期列表失败：{str(e)}"}


@app.tool()
async def get_grades_by_semester(semester_code: str) -> Dict[str, Any]:
    """
    获取指定学期的成绩详情
    
    Args:
        semester_code: 学期代码，如"2023-20241"（可通过 get_semester_list 获取）
        
    Returns:
        该学期的详细成绩列表
    """
    print(f"Fetching grades for semester: {semester_code}", file=sys.stderr)
    try:
        client = get_client()
        ensure_logged_in(client)
        
        grades = client.get_grades_by_semester(semester_code)
        print(f"Found {len(grades)} courses for semester {semester_code}", file=sys.stderr)
        
        # 转换为字典格式
        grades_dict = [asdict(grade) for grade in grades]
        
        return {
            "success": True,
            "semester_code": semester_code,
            "grades": grades_dict,
            "total_courses": len(grades)
        }
    except Exception as e:
        print(f"Error fetching grades for semester {semester_code}: {e}", file=sys.stderr)
        return {"success": False, "message": f"获取学期成绩失败：{str(e)}"}


@app.tool()
async def export_grades_to_csv(filename: str = "grades.csv") -> Dict[str, Any]:
    """
    导出所有成绩为 CSV 文件
    
    Args:
        filename: 导出的文件名（默认为 grades.csv）
        
    Returns:
        导出结果和文件路径
    """
    print(f"Exporting grades to CSV: {filename}", file=sys.stderr)
    try:
        client = get_client()
        ensure_logged_in(client)
        
        filepath = client.export_grades_to_csv(filename)
        print(f"Grades exported to: {filepath}", file=sys.stderr)
        return {
            "success": True,
            "message": "成绩导出成功",
            "filepath": filepath,
            "filename": filename
        }
    except Exception as e:
        print(f"Error exporting grades: {e}", file=sys.stderr)
        return {"success": False, "message": f"导出成绩失败：{str(e)}"}


# ==================== 学期相关工具 ====================

@app.tool()
async def get_current_semester(force_reload: bool = False) -> Dict[str, Any]:
    """
    获取当前学年学期信息
    
    Args:
        force_reload: 是否强制重新加载（默认使用缓存）
        
    Returns:
        当前学年学期的详细信息
    """
    print(f"Fetching current semester (force_reload={force_reload})", file=sys.stderr)
    try:
        client = get_client()
        ensure_logged_in(client)
        
        current_semester = client.get_current_semester(force_reload=force_reload)
        print(f"Current semester: {current_semester.academic_year}-{current_semester.semester_code}", file=sys.stderr)
        
        return {
            "success": True,
            "current_semester": asdict(current_semester)
        }
    except Exception as e:
        print(f"Error fetching current semester: {e}", file=sys.stderr)
        return {"success": False, "message": f"获取当前学期失败：{str(e)}"}


@app.tool()
async def get_all_semesters() -> Dict[str, Any]:
    """
    获取所有可用学期信息
    
    Returns:
        所有学期的详细信息列表
    """
    print("Fetching all semesters", file=sys.stderr)
    try:
        client = get_client()
        ensure_logged_in(client)
        
        semesters = client.get_all_semesters()
        print(f"Found {len(semesters)} semesters", file=sys.stderr)
        
        # 转换为字典格式
        semesters_dict = [asdict(semester) for semester in semesters]
        
        return {
            "success": True,
            "semesters": semesters_dict,
            "total_semesters": len(semesters)
        }
    except Exception as e:
        print(f"Error fetching all semesters: {e}", file=sys.stderr)
        return {"success": False, "message": f"获取学期信息失败：{str(e)}"}


@app.tool()
async def get_semester_first_day(academic_year: str = None, semester: str = None, force_reload: bool = False) -> Dict[str, Any]:
    """
    获取指定学期的第一天信息
    
    Args:
        academic_year: 学年，如"2024-2025"（默认为当前学年）
        semester: 学期代码，如"1"或"2"（默认为当前学期）
        force_reload: 是否强制重新加载
        
    Returns:
        学期第一天的详细信息
    """
    print(f"Fetching semester first day for {academic_year}-{semester}", file=sys.stderr)
    try:
        client = get_client()
        ensure_logged_in(client)
        
        first_day_info = client.get_semester_first_day(
            academic_year=academic_year, 
            semester=semester, 
            force_reload=force_reload
        )
        print(f"Semester first day: {first_day_info.first_day_str}", file=sys.stderr)
        
        return {
            "success": True,
            "semester_first_day": asdict(first_day_info)
        }
    except Exception as e:
        print(f"Error fetching semester first day: {e}", file=sys.stderr)
        return {"success": False, "message": f"获取学期第一天失败：{str(e)}"}


@app.tool()
async def calculate_week_and_weekday(target_date: str, academic_year: str = None, semester: str = None) -> Dict[str, Any]:
    """
    计算指定日期在学期中的周次和星期信息
    
    Args:
        target_date: 目标日期，格式为"YYYY-MM-DD"
        academic_year: 学年，如"2024-2025"（默认为当前学年）
        semester: 学期代码，如"1"或"2"（默认为当前学期）
        
    Returns:
        周次和星期的详细信息
    """
    print(f"Calculating week and weekday for {target_date}", file=sys.stderr)
    try:
        client = get_client()
        ensure_logged_in(client)
        
        weekday_info = client.calculate_week_and_weekday(
            target_date=target_date,
            academic_year=academic_year,
            semester=semester
        )
        print(f"Week {weekday_info.week_number}, {weekday_info.weekday_name}", file=sys.stderr)
        
        return {
            "success": True,
            "weekday_info": asdict(weekday_info)
        }
    except Exception as e:
        print(f"Error calculating week and weekday: {e}", file=sys.stderr)
        return {"success": False, "message": f"计算周次和星期失败：{str(e)}"}


# ==================== 教室相关工具 ====================

@app.tool()
async def get_teaching_buildings(force_reload: bool = False) -> Dict[str, Any]:
    """
    获取所有教学楼信息
    
    Args:
        force_reload: 是否强制重新加载（默认使用缓存）
        
    Returns:
        教学楼列表信息
    """
    print(f"Fetching teaching buildings (force_reload={force_reload})", file=sys.stderr)
    try:
        client = get_client()
        ensure_logged_in(client)
        
        buildings = client.get_teaching_buildings(force_reload=force_reload)
        print(f"Found {len(buildings)} teaching buildings", file=sys.stderr)
        
        # 转换为字典格式
        buildings_dict = [asdict(building) for building in buildings]
        
        return {
            "success": True,
            "teaching_buildings": buildings_dict,
            "total_buildings": len(buildings)
        }
    except Exception as e:
        print(f"Error fetching teaching buildings: {e}", file=sys.stderr)
        return {"success": False, "message": f"获取教学楼信息失败：{str(e)}"}


@app.tool()
async def query_classroom_availability(
    academic_year: str = None, 
    semester: str = None,
    building_code: str = None, 
    week_numbers: List[int] = None,
    week_string: str = None, 
    use_cache: bool = True
) -> Dict[str, Any]:
    """
    查询教室可用性信息
    
    Args:
        academic_year: 学年，如"2024-2025"（默认为当前学年）
        semester: 学期代码，如"1"或"2"（默认为当前学期）
        building_code: 教学楼代码，如"17"（用户不知道教学楼代码，你必须通过 get_teaching_buildings 获取教学楼列表，找到对应教学楼的教学楼代码）
        week_numbers: 周次列表，如 [1,2,3]
        week_string: 周次字符串，如"1-3,5,7-9"（与 week_numbers 二选一）
        use_cache: 是否使用缓存（默认 true）
        
    Returns:
        教室可用性的详细信息
    """
    print(f"Querying classroom availability for building {building_code}", file=sys.stderr)
    try:
        client = get_client()
        ensure_logged_in(client)
        
        availability = client.query_classroom_availability(
            academic_year=academic_year,
            semester=semester,
            building_code=building_code,
            week_numbers=week_numbers,
            week_string=week_string,
            use_cache=use_cache
        )
        
        print(f"Found {len(availability.classrooms)} classrooms", file=sys.stderr)
        
        return {
            "success": True,
            "availability": {
                "academic_year": availability.academic_year,
                "semester": availability.semester,
                "building_code": availability.building_code,
                "week_mask": availability.week_mask,
                "query_time": availability.query_time,
                "classrooms": [asdict(room) for room in availability.classrooms],
                "occupancies": [asdict(occ) for occ in availability.occupancies],
                "total_classrooms": len(availability.classrooms),
                "total_occupancies": len(availability.occupancies)
            }
        }
    except Exception as e:
        print(f"Error querying classroom availability: {e}", file=sys.stderr)
        return {"success": False, "message": f"查询教室可用性失败：{str(e)}"}


@app.tool()
async def get_available_classrooms(
    academic_year: str = None,
    semester: str = None,
    building_code: str = None,
    week_numbers: List[int] = None,
    week_string: str = None,
    weekday: int = None,
    period: int = None,
    min_seats: int = None,
    use_cache: bool = True
) -> Dict[str, Any]:
    """
    获取符合条件的可用教室列表
    
    Args:
        academic_year: 学年，如"2024-2025"（默认为当前学年）
        semester: 学期代码，如"1"或"2"（默认为当前学期）
        building_code: 教学楼代码，如"17"（用户不知道教学楼代码，你必须通过 get_teaching_buildings 获取教学楼列表，找到对应教学楼的教学楼代码）
        week_numbers: 周次列表，如 [1,2,3]
        week_string: 周次字符串，如"1-3,5,7-9"
        weekday: 星期几（1-7，1 为周一）
        period: 节次（1-13）
        min_seats: 最少座位数
        use_cache: 是否使用缓存
        
    Returns:
        符合条件的可用教室列表
    """
    print(f"Getting available classrooms with filters", file=sys.stderr)
    try:
        client = get_client()
        ensure_logged_in(client)
        
        available_rooms = client.get_available_classrooms(
            academic_year=academic_year,
            semester=semester,
            building_code=building_code,
            week_numbers=week_numbers,
            week_string=week_string,
            weekday=weekday,
            period=period,
            min_seats=min_seats,
            use_cache=use_cache
        )
        
        print(f"Found {len(available_rooms)} available classrooms", file=sys.stderr)
        
        # 转换为字典格式
        rooms_dict = [asdict(room) for room in available_rooms]
        
        return {
            "success": True,
            "available_classrooms": rooms_dict,
            "total_available": len(available_rooms),
            "filters_applied": {
                "academic_year": academic_year,
                "semester": semester,
                "building_code": building_code,
                "week_numbers": week_numbers,
                "week_string": week_string,
                "weekday": weekday,
                "period": period,
                "min_seats": min_seats
            }
        }
    except Exception as e:
        print(f"Error getting available classrooms: {e}", file=sys.stderr)
        return {"success": False, "message": f"获取可用教室失败：{str(e)}"}


# ==================== 工具方法 ====================

@app.tool()
async def generate_week_mask(week_numbers: List[int]) -> Dict[str, Any]:
    """
    根据周次列表生成周次掩码
    
    Args:
        week_numbers: 周次列表，如 [1,2,3,5,7,8,9]
        
    Returns:
        生成的周次掩码字符串
    """
    print(f"Generating week mask for weeks: {week_numbers}", file=sys.stderr)
    try:
        client = get_client()
        
        week_mask = client.generate_week_mask(week_numbers)
        print(f"Generated week mask: {week_mask}", file=sys.stderr)
        
        return {
            "success": True,
            "week_numbers": week_numbers,
            "week_mask": week_mask
        }
    except Exception as e:
        print(f"Error generating week mask: {e}", file=sys.stderr)
        return {"success": False, "message": f"生成周次掩码失败：{str(e)}"}


@app.tool()
async def parse_week_numbers(week_string: str) -> Dict[str, Any]:
    """
    解析周次字符串为周次列表
    
    Args:
        week_string: 周次字符串，如"1-3,5,7-9"
        
    Returns:
        解析出的周次列表
    """
    print(f"Parsing week string: {week_string}", file=sys.stderr)
    try:
        client = get_client()
        
        week_numbers = client.parse_week_numbers(week_string)
        print(f"Parsed week numbers: {week_numbers}", file=sys.stderr)
        
        return {
            "success": True,
            "week_string": week_string,
            "week_numbers": week_numbers
        }
    except Exception as e:
        print(f"Error parsing week string: {e}", file=sys.stderr)
        return {"success": False, "message": f"解析周次字符串失败：{str(e)}"}


@app.tool()
async def refresh_data() -> Dict[str, Any]:
    """
    刷新所有缓存数据
    
    Returns:
        刷新操作的结果
    """
    print("Refreshing all cached data", file=sys.stderr)
    try:
        client = get_client()
        ensure_logged_in(client)
        
        client.refresh_data()
        print("Data refreshed successfully", file=sys.stderr)
        
        return {
            "success": True,
            "message": "所有缓存数据已刷新"
        }
    except Exception as e:
        print(f"Error refreshing data: {e}", file=sys.stderr)
        return {"success": False, "message": f"刷新数据失败：{str(e)}"}


@app.tool()
async def get_server_info() -> Dict[str, Any]:
    """
    获取服务器信息和可用功能列表
    
    Returns:
        服务器详细信息
    """
    print("Fetching server info", file=sys.stderr)
    return {
        "name": "哈工大（深圳）教务系统 API 服务",
        "version": "3.0.0",
        "description": "基于 JWClient 的完整教务系统 API，支持成绩、学期、教室等全功能",
        "features": [
            "自动从.env 文件读取登录凭据",
            "智能缓存机制，避免重复请求",
            "完整的成绩和 GPA 信息获取",
            "学期信息查询和日期计算",
            "教室可用性查询和筛选",
            "数据导出和工具方法"
        ],
        "tool_categories": {
            "成绩相关": [
                "get_all_grades - 获取所有成绩和 GPA 信息",
                "get_gpa_info - 获取 GPA 和排名信息",
                "get_semester_list - 获取有成绩的学期列表",
                "get_grades_by_semester - 获取指定学期成绩",
                "export_grades_to_csv - 导出成绩为 CSV 文件"
            ],
            "学期相关": [
                "get_current_semester - 获取当前学年学期",
                "get_all_semesters - 获取所有可用学期",
                "get_semester_first_day - 获取学期第一天",
                "calculate_week_and_weekday - 计算日期的周次和星期"
            ],
            "教室相关": [
                "get_teaching_buildings - 获取教学楼列表",
                "query_classroom_availability - 查询教室可用性",
                "get_available_classrooms - 获取符合条件的可用教室"
            ],
            "工具方法": [
                "generate_week_mask - 生成周次掩码",
                "parse_week_numbers - 解析周次字符串",
                "refresh_data - 刷新所有缓存数据",
                "get_server_info - 获取服务器信息"
            ]
        },
        "setup_instructions": {
            "step1": "安装依赖：pip install python-dotenv mcp requests",
            "step2": "创建.env 文件，内容如下：",
            "env_content": [
                "HITSZ_USERNAME=your_student_id",
                "HITSZ_PASSWORD=your_password"
            ],
            "step3": "运行服务：python mcp_jw_service.py"
        },
        "usage_tips": [
            "首次使用建议先调用 get_all_grades 加载基础数据",
            "用户不知道教学楼代号，教室查询必须先获取教学楼列表确定 building_code",
            "周次可以用列表 [1,2,3] 或字符串'1-3,5'格式",
            "大部分功能支持缓存，可设置 force_reload=true 强制刷新"
        ]
    }


if __name__ == "__main__":
    try:
        print("Starting MCP server...", file=sys.stderr)
        
        # 检查凭据配置
        try:
            username, password = get_credentials()
            print(f"Credentials loaded for user: {username}", file=sys.stderr)
        except ValueError as e:
            print(f"Configuration error: {e}", file=sys.stderr)
            print("Server will start but tools will fail until credentials are configured", file=sys.stderr)
        
        # 运行 MCP 服务
        app.run(transport='stdio')
    except Exception as e:
        print(f"Error running MCP server: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1) 