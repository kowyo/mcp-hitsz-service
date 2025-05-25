# 哈工大（深圳）教务系统 MCP 服务

基于缓存优化的哈工大（深圳）教务系统API服务，支持自动登录和智能数据缓存。

## 功能特性

- 🚀 **智能缓存机制**: 避免重复请求，提升性能
- 🔐 **自动登录**: 从 `.env` 文件读取凭据，无需手动登录
- 📊 **完整数据**: 获取成绩、GPA、排名等完整信息
- 📁 **数据导出**: 支持导出成绩为 CSV 格式
- 🔧 **MCP 兼容**: 完全兼容 Model Context Protocol

## 安装依赖

```bash
pip install python-dotenv mcp requests beautifulsoup4
```

## 配置设置

### 1. 创建 `.env` 文件

在项目根目录创建 `.env` 文件，内容如下：

```env
# 哈工大（深圳）教务系统登录凭据
HITSZ_USERNAME=your_student_id
HITSZ_PASSWORD=your_password
```

**注意**: 
- 请将 `your_student_id` 替换为你的学号
- 请将 `your_password` 替换为你的密码
- `.env` 文件包含敏感信息，请勿提交到版本控制系统

### 2. 环境变量方式（可选）

如果不使用 `.env` 文件，也可以直接设置环境变量：

```bash
export HITSZ_USERNAME=your_student_id
export HITSZ_PASSWORD=your_password
```

## 使用方法

### 作为 MCP 服务运行

```bash
python mcp_jw_service.py
```

### 可用工具

| 工具名称 | 描述 | 缓存状态 |
|---------|------|---------|
| `get_all_grades` | 加载所有数据并返回摘要信息 | 基础数据源 |
| `get_gpa_info` | 获取GPA和排名信息 | 基于缓存 |
| `get_semester_list` | 获取学期列表 | 基于缓存 |
| `get_grades_by_semester` | 获取指定学期成绩 | 基于缓存 |
| `export_grades_to_csv` | 导出成绩为CSV | 基于缓存 |
| `get_server_info` | 获取服务器信息 | - |

### 缓存机制说明

1. **首次调用**: `get_all_grades` 会从教务系统获取数据并缓存，返回数据摘要
2. **后续调用**: 其他工具都基于缓存数据工作，无需重复请求
3. **数据刷新**: 重启服务可刷新缓存
4. **上下文优化**: `get_all_grades` 只返回摘要信息，避免上下文过长

## 数据结构

### 成绩信息 (CourseGrade)

```json
{
  "course_id": "课程代码",
  "course_name": "课程名称", 
  "course_name_en": "课程英文名称",
  "credit": 3.0,
  "semester": "2023-20241",
  "semester_display": "2023-2024学年第1学期",
  "score": "85",
  "score_raw": "85",
  "exam_type": "考试",
  "course_type": "必修",
  "course_category": "专业课",
  "department": "计算机科学与技术学院",
  "is_pass": true,
  "is_restudy": false,
  "rank": "15",
  "total_students": "120"
}
```

### GPA信息 (GPAInfo)

```json
{
  "gpa": 3.85,
  "all_course_gpa": 3.82,
  "avg_score": 87.5,
  "all_course_avg_score": 86.8,
  "rank": 25,
  "total_students": 300,
  "rank_percentage": 8.33,
  "passed_courses": 45,
  "total_credits": 120.5
}
```

## 示例响应

### get_all_grades

```json
{
  "success": true,
  "message": "数据已成功加载到缓存",
  "summary": {
    "total_courses": 45,
    "total_credits": 120.5,
    "passed_courses": 43,
    "failed_courses": 2,
    "restudy_courses": 1,
    "required_courses": 35,
    "elective_courses": 10,
    "semesters_count": 6,
    "semester_summary": [
      {"code": "2023-20241", "name": "2023-2024学年第1学期", "courses": 8},
      {"code": "2022-20232", "name": "2022-2023学年第2学期", "courses": 7}
    ]
  },
  "gpa_summary": {
    "gpa": 3.85,
    "all_course_gpa": 3.82,
    "rank": 25,
    "total_students": 300,
    "rank_percentage": 8.33,
    "avg_score": 87.5
  }
}
```

### get_semester_list

```json
{
  "success": true,
  "semesters": [
    {"code": "2023-20241", "name": "2023-2024学年第1学期"},
    {"code": "2022-20232", "name": "2022-2023学年第2学期"},
    ...
  ]
}
```

## 错误处理

服务会自动处理以下情况：

1. **凭据未配置**: 提供详细的配置说明
2. **登录失败**: 自动重试登录
3. **网络错误**: 返回友好的错误信息
4. **数据解析错误**: 跳过有问题的记录，继续处理其他数据

## 性能优化

- ✅ 智能缓存：避免重复网络请求
- ✅ 批量获取：一次请求获取所有数据
- ✅ 懒加载：只在需要时才获取数据
- ✅ 内存缓存：数据在内存中保持，直到服务重启

## 安全注意事项

1. **凭据保护**: `.env` 文件包含敏感信息，请勿分享或提交到代码仓库
2. **网络安全**: 服务通过HTTPS与教务系统通信
3. **数据隐私**: 所有数据仅在本地处理，不会发送到第三方服务器

## 故障排除

### 常见问题

1. **ImportError: No module named 'dotenv'**
   ```bash
   pip install python-dotenv
   ```

2. **登录失败**
   - 检查 `.env` 文件中的用户名和密码是否正确
   - 确认教务系统可以正常访问

3. **数据获取失败**
   - 检查网络连接
   - 确认教务系统服务正常

### 调试模式

服务会在 stderr 输出详细的调试信息，包括：
- 登录状态
- 数据获取进度
- 错误详情

## 版本历史

### v2.0.0
- 添加智能缓存机制
- 支持 `.env` 文件自动登录
- 移除手动登录工具
- 优化性能和用户体验

### v1.0.0
- 基础功能实现
- 支持手动登录
- 基本的成绩和GPA查询

## 许可证

本项目仅供学习和个人使用，请遵守学校相关规定。
