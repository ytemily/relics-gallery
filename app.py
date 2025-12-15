from flask import Flask, render_template, request, abort, session, redirect, url_for, flash, jsonify
import mysql.connector
from mysql.connector import Error
import os
import re
from werkzeug.security import generate_password_hash, check_password_hash
from query_builder import build_search_query, build_cultures_browse_query, build_culture_artifacts_query
import pandas as pd
from datetime import datetime
from werkzeug.utils import secure_filename
from functools import wraps

# 文化描述映射（用于文化浏览页面）
CULTURE_DESCRIPTIONS = {
    '中华文化': '包含中原、楚、巴蜀、吴越等地域文化遗产。',
    '日本文化': '绳文陶器、浮世绘、刀剑与漆器艺术。',
    '西亚文化': '美索不达米亚、波斯与伊斯兰文明的瑰宝。',
    '埃及文化': '尼罗河流域的法老文明、神庙与墓葬艺术。',
    '希腊罗马文化': '古典雕塑、建筑构件与地中海文明遗存。',
    '印度文化': '佛教造像、印度教神像与南亚次大陆艺术。',
}

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'your-secret-key-change-in-production-2024')

# 数据库配置（支持环境变量）
db_config = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', 'leeanna'),
    'database': os.getenv('DB_NAME', 'project')
}

def get_db_connection():
    """建立数据库连接"""
    try:
        conn = mysql.connector.connect(**db_config)
        return conn
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
        return None

def normalize_image_path(path):
    """
    规范化图片路径，确保路径格式正确
    将Windows路径的反斜杠转换为正斜杠，移除开头的斜杠
    返回相对于static文件夹的路径（例如：met_images/472562.jpg）
    """
    if not path:
        return None
    
    # 转换为字符串并去除首尾空格
    path = str(path).strip()
    
    # 将反斜杠转换为正斜杠
    path = path.replace('\\', '/')
    
    # 移除开头的斜杠
    path = path.lstrip('/')
    
    # 如果路径包含 'static/'，提取后面的部分
    if 'static/' in path.lower():
        # 不区分大小写查找
        parts = path.split('/')
        try:
            # 查找 static 的位置（不区分大小写）
            static_index = next(i for i, part in enumerate(parts) if part.lower() == 'static')
            if static_index + 1 < len(parts):
                path = '/'.join(parts[static_index + 1:])
        except StopIteration:
            pass
    
    # 如果路径是绝对路径（包含盘符），尝试提取相对路径
    # 例如：D:/a_schoolworks/.../static/met_images/472562.jpg -> met_images/472562.jpg
    if ':' in path:
        # 查找 static/ 后面的部分
        parts = path.split('/')
        try:
            static_index = next(i for i, part in enumerate(parts) if part.lower() == 'static')
            if static_index + 1 < len(parts):
                path = '/'.join(parts[static_index + 1:])
        except StopIteration:
            # 如果没有找到 static，尝试查找 met_images
            try:
                met_index = next(i for i, part in enumerate(parts) if part.lower() == 'met_images')
                if met_index < len(parts):
                    path = '/'.join(parts[met_index:])
            except StopIteration:
                pass
    
    # 确保路径不为空
    if not path:
        return None

    # 如果路径已经以 images/ 开头，不再添加
    if not path.startswith('images/'):
        path = 'images/' + path
    
    return path

@app.route('/')
def homepage():
    """
    动态主页：沉浸式首屏和自由浏览入口
    """
    conn = get_db_connection()
    if conn is None:
        # 如果数据库连接失败，仍然可以显示页面，只是没有背景图片
        return render_template('homepage.html', 
                             random_images=[], 
                             culture_images=[],
                             geography_images=[])
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        # 获取随机浏览的代表性图片（随机获取4-6张图片）
        random_query = """
            SELECT iv.Local_Path as local_path
            FROM IMAGE_VERSIONS iv
            INNER JOIN ARTIFACTS a ON iv.Artifact_PK = a.Artifact_PK
            WHERE iv.Local_Path IS NOT NULL AND iv.Local_Path != ''
            ORDER BY RAND()
            LIMIT 6
        """
        cursor.execute(random_query)
        random_images = cursor.fetchall()
        
        # 获取文化浏览的代表性图片（从不同文化中获取图片）
        culture_query = """
            SELECT DISTINCT iv.Local_Path as local_path
            FROM IMAGE_VERSIONS iv
            INNER JOIN ARTIFACTS a ON iv.Artifact_PK = a.Artifact_PK
            INNER JOIN PROPERTIES p ON a.Artifact_PK = p.Artifact_PK
            WHERE iv.Local_Path IS NOT NULL AND iv.Local_Path != '' 
                AND p.Culture IS NOT NULL AND p.Culture != ''
            GROUP BY p.Culture, iv.Local_Path
            ORDER BY RAND()
            LIMIT 6
        """
        cursor.execute(culture_query)
        culture_images = cursor.fetchall()
        
        # 获取地理浏览的代表性图片（从不同地理区域中获取图片）
        geography_query = """
            SELECT DISTINCT iv.Local_Path as local_path
            FROM IMAGE_VERSIONS iv
            INNER JOIN ARTIFACTS a ON iv.Artifact_PK = a.Artifact_PK
            INNER JOIN PROPERTIES p ON a.Artifact_PK = p.Artifact_PK
            WHERE iv.Local_Path IS NOT NULL AND iv.Local_Path != '' 
                AND p.Geography IS NOT NULL AND p.Geography != ''
            GROUP BY p.Geography, iv.Local_Path
            ORDER BY RAND()
            LIMIT 6
        """
        cursor.execute(geography_query)
        geography_images = cursor.fetchall()
        
        # 规范化图片路径
        for img in random_images:
            if img.get('local_path'):
                img['local_path'] = normalize_image_path(img['local_path'])
        
        for img in culture_images:
            if img.get('local_path'):
                img['local_path'] = normalize_image_path(img['local_path'])
        
        for img in geography_images:
            if img.get('local_path'):
                img['local_path'] = normalize_image_path(img['local_path'])
        
        cursor.close()
        conn.close()
        
        return render_template('homepage.html', 
                             random_images=[img['local_path'] for img in random_images if img.get('local_path')],
                             culture_images=[img['local_path'] for img in culture_images if img.get('local_path')],
                             geography_images=[img['local_path'] for img in geography_images if img.get('local_path')])
    except Error as e:
        if conn:
            conn.close()
        # 即使查询失败，也显示页面
        return render_template('homepage.html', 
                             random_images=[], 
                             culture_images=[],
                             geography_images=[])

@app.route('/explore')
@app.route('/random')
def random_browse():
    """
    随机浏览页面：随机排序展示所有文物条目
    """
    conn = get_db_connection()
    if conn is None:
        return render_template('error.html', 
                             error_message="无法连接到数据库。请检查数据库配置和连接状态。"), 500
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        # 随机排序查询（使用RAND()函数）
        query = """
            SELECT 
                a.Artifact_PK AS artifact_id, 
                a.Title_CN AS title, 
                a.Date_CN AS date_text, 
                ANY_VALUE(iv.Local_Path) AS local_path
            FROM ARTIFACTS a
            LEFT JOIN IMAGE_VERSIONS iv ON a.Artifact_PK = iv.Artifact_PK
            GROUP BY a.Artifact_PK
            ORDER BY RAND()
        """
        
        cursor.execute(query)
        artifacts = cursor.fetchall()
        
        # 规范化图片路径
        for artifact in artifacts:
            if artifact.get('local_path'):
                artifact['local_path'] = normalize_image_path(artifact['local_path'])
        
        cursor.close()
        conn.close()
        
        return render_template('index.html', artifacts=artifacts, page_title='随机浏览')
    except Error as e:
        if conn:
            conn.close()
        return render_template('error.html', 
                             error_message=f"数据库查询错误: {str(e)}"), 500

@app.route('/artifact/<int:artifact_id>')
def detail(artifact_id):
    """
    详情页面：读取特定文物的详细信息
    """
    conn = get_db_connection()
    if conn is None:
        return render_template('error.html', 
                             error_message="无法连接到数据库。请检查数据库配置和连接状态。"), 500
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        # 查询文物的基本信息（不包含图片）
        query = """
            SELECT 
                a.Artifact_PK AS artifact_id,
                a.Source_ID AS source_id,
                a.Original_ID AS original_id,
                a.Title_CN AS title,
                a.Title_EN AS title_en,
                a.Description_CN AS description,
                a.Classification AS classification,
                a.Material AS medium,
                a.Date_CN AS date_text,
                a.Date_EN AS date_en,
                p.Geography AS geography,
                p.Culture AS culture_name,
                p.Artist AS artist_name,
                p.Credit_Line AS credit_text,
                p.Page_Link AS source_url,
                s.Museum_Name_CN AS dept_name
            FROM ARTIFACTS a
            LEFT JOIN PROPERTIES p ON a.Artifact_PK = p.Artifact_PK
            LEFT JOIN SOURCES s ON a.Source_ID = s.Source_ID
            WHERE a.Artifact_PK = %s
        """
        
        cursor.execute(query, (artifact_id,))
        artifact = cursor.fetchone()
        
        if artifact is None:
            cursor.close()
            conn.close()
            abort(404)
        
        # 查询该文物的所有图片
        images_query = """
            SELECT Local_Path AS local_path
            FROM IMAGE_VERSIONS
            WHERE Artifact_PK = %s
            ORDER BY Version_PK
        """
        cursor.execute(images_query, (artifact_id,))
        images = cursor.fetchall()
        
        # 规范化所有图片路径
        image_paths = []
        for img in images:
            if img.get('local_path'):
                normalized_path = normalize_image_path(img['local_path'])
                if normalized_path:
                    image_paths.append(normalized_path)
        
        # 设置主图和缩略图列表
        if image_paths:
            artifact['local_path'] = image_paths[0]  # 第一张作为主图
            artifact['image_paths'] = image_paths  # 所有图片作为缩略图列表
        else:
            artifact['local_path'] = None
            artifact['image_paths'] = []
        
        # 查询尺寸信息
        dimensions_query = """
            SELECT Size_Type, Size_Value, Size_Unit
            FROM DIMENSIONS
            WHERE Artifact_PK = %s
            ORDER BY Dimension_PK
        """
        cursor.execute(dimensions_query, (artifact_id,))
        dimensions = cursor.fetchall()
        
        # 格式化尺寸信息为字符串
        if dimensions:
            dim_parts = []
            for dim in dimensions:
                if dim.get('Size_Value') and dim.get('Size_Unit'):
                    dim_parts.append(f"{dim['Size_Type']}: {dim['Size_Value']} {dim['Size_Unit']}")
                elif dim.get('Size_Value'):
                    dim_parts.append(f"{dim['Size_Type']}: {dim['Size_Value']}")
            artifact['dimensions'] = '; '.join(dim_parts) if dim_parts else None
        else:
            artifact['dimensions'] = None
        
        cursor.close()
        conn.close()
            
        return render_template('detail.html', artifact=artifact)
    except Error as e:
        if conn:
            conn.close()
        return render_template('error.html', 
                             error_message=f"数据库查询错误: {str(e)}"), 500

@app.route('/search')
def search():
    """
    搜索页面：根据关键词搜索文物
    支持在标题、艺术家、文化、部门、年代、描述、材质中搜索
    支持高级筛选（年代、文化、材质、地区）和排序功能
    """
    search_term = request.args.get('q', '').strip()
    
    # 获取筛选参数
    era_filters = request.args.getlist('era')
    culture_filters = request.args.getlist('culture')
    material_filters = request.args.getlist('material')
    region_filters = request.args.getlist('region')
    
    # 获取排序参数
    sort_by = request.args.get('sort', 'relevance')
    
    # 构建激活的筛选字典（用于显示筛选标签）
    active_filters = {}
    if era_filters:
        active_filters['era'] = era_filters
    if culture_filters:
        active_filters['culture'] = culture_filters
    if material_filters:
        active_filters['material'] = material_filters
    if region_filters:
        active_filters['region'] = region_filters
    
    if not search_term:
        # 如果没有搜索关键词，重定向到首页
        return redirect(url_for('homepage'))
    
    conn = get_db_connection()
    if conn is None:
        return render_template('error.html', 
                             error_message="无法连接到数据库。请检查数据库配置和连接状态。"), 500
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        # 构建搜索查询
        query = build_search_query(search_term)
        if query is None:
            cursor.close()
            conn.close()
            return redirect(url_for('homepage'))
        
        # TODO: 在这里添加筛选条件到查询中
        # 目前暂时不实现实际的SQL筛选，保留接口
        
        # 执行搜索查询，使用10个参数（对应WHERE子句中的10个LIKE条件）
        search_pattern = f"%{search_term}%"
        cursor.execute(query, (search_pattern,) * 10)
        artifacts = cursor.fetchall()
        
        # 规范化图片路径
        for artifact in artifacts:
            if artifact.get('local_path'):
                artifact['local_path'] = normalize_image_path(artifact['local_path'])
        
        # 获取筛选选项数据（基于原始搜索结果，在筛选前计算）
        try:
            filter_options = get_filter_options_from_results(artifacts)
        except Exception as e:
            print(f"Error getting filter options: {e}")
            # 如果获取失败，使用空数据
            filter_options = {
                'eras': [],
                'cultures': [],
                'materials': [],
                'regions': []
            }
        
        # 应用筛选条件（在计算筛选选项之后）
        if culture_filters or material_filters:
            filtered_artifacts = []
            for artifact in artifacts:
                # 检查文化筛选
                if culture_filters:
                    artifact_culture = artifact.get('culture_name', '') or ''
                    artifact_culture = artifact_culture.strip()
                    if artifact_culture not in culture_filters:
                        continue
                
                # 检查材质筛选
                if material_filters:
                    artifact_material = artifact.get('medium', '') or ''
                    artifact_material = artifact_material.strip()
                    if artifact_material not in material_filters:
                        continue
                
                filtered_artifacts.append(artifact)
            
            artifacts = filtered_artifacts
        
        # 应用排序逻辑
        if sort_by == 'era_asc':
            # 按年代从早到晚排序（start_year 升序）
            artifacts = sorted(artifacts, key=lambda x: (
                x.get('start_year') is None,  # None 值放到最后
                x.get('start_year') or float('inf')  # 按 start_year 升序
            ))
        elif sort_by == 'era_desc':
            # 按年代从晚到早排序（start_year 降序）
            artifacts = sorted(artifacts, key=lambda x: (
                x.get('start_year') is None,  # None 值放到最后
                -(x.get('start_year') or float('-inf'))  # 按 start_year 降序
            ))
        elif sort_by == 'newest':
            # 按最新入库排序（artifact_id 降序）
            artifacts = sorted(artifacts, key=lambda x: x.get('artifact_id', 0), reverse=True)
        # 'relevance' 或其他：保持默认排序
        
        cursor.close()
        conn.close()
        
        # 渲染搜索结果页面
        return render_template('search.html', 
                             artifacts=artifacts, 
                             search_term=search_term,
                             active_filters=active_filters,
                             filter_options=filter_options,
                             sort_by=sort_by)
    except Error as e:
        if conn:
            conn.close()
        return render_template('error.html', 
                             error_message=f"数据库查询错误: {str(e)}"), 500

def get_filter_options_from_results(artifacts):
    """
    从搜索结果中提取筛选选项数据
    返回各个筛选类别的选项及其数量（仅包含搜索结果中出现的）
    """
    # 统计文化和材质
    culture_count = {}
    material_count = {}
    
    for artifact in artifacts:
        # 统计文化
        culture = artifact.get('culture_name')
        if culture and culture.strip():
            culture = culture.strip()
            culture_count[culture] = culture_count.get(culture, 0) + 1
        
        # 统计材质
        material = artifact.get('medium')
        if material and material.strip():
            material = material.strip()
            material_count[material] = material_count.get(material, 0) + 1
    
    # 转换为列表格式，按数量降序排列
    cultures = [
        {
            'value': culture,
            'label': culture,
            'count': count
        }
        for culture, count in sorted(culture_count.items(), key=lambda x: (-x[1], x[0]))
    ]
    
    materials = [
        {
            'value': material,
            'label': material,
            'count': count
        }
        for material, count in sorted(material_count.items(), key=lambda x: (-x[1], x[0]))
    ]
    
    # 年代筛选暂时使用空列表（暂时不用接入实现）
    eras = []
    
    # 地区筛选暂时使用空列表
    regions = []
    
    return {
        'eras': eras,
        'cultures': cultures,
        'materials': materials,
        'regions': regions
    }

@app.route('/browse')
def browse_cultures():
    """
    文化浏览页面：显示所有文化分类
    每个文化显示名称、文物数量、代表性图片和描述
    """
    conn = get_db_connection()
    if conn is None:
        return render_template('error.html', 
                             error_message="无法连接到数据库。请检查数据库配置和连接状态。"), 500
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        # 构建文化浏览查询（从PROPERTIES表获取文化信息）
        query = """
            SELECT 
                p.Culture AS culture_name,
                COUNT(DISTINCT a.Artifact_PK) AS artifact_count,
                ANY_VALUE(iv.Local_Path) AS representative_image
            FROM PROPERTIES p
            LEFT JOIN ARTIFACTS a ON p.Artifact_PK = a.Artifact_PK
            LEFT JOIN IMAGE_VERSIONS iv ON a.Artifact_PK = iv.Artifact_PK
            WHERE p.Culture IS NOT NULL AND p.Culture != ''
            GROUP BY p.Culture
            HAVING artifact_count > 0
            ORDER BY artifact_count DESC, p.Culture
        """
        cursor.execute(query)
        cultures_raw = cursor.fetchall()
        
        # 转换数据格式，添加culture_id（使用culture_name的hash作为临时ID）
        cultures = []
        for idx, culture in enumerate(cultures_raw, 1):
            culture_dict = {
                'culture_id': idx,  # 临时ID，实际应该根据culture_name生成唯一ID
                'culture_name': culture['culture_name'],
                'artifact_count': culture['artifact_count'],
                'representative_image': culture['representative_image']
            }
            cultures.append(culture_dict)
        
        # 为每个文化添加描述和规范化图片路径
        for culture in cultures:
            culture_name = culture.get('culture_name', '')
            # 添加描述（如果映射中存在）
            culture['description'] = CULTURE_DESCRIPTIONS.get(culture_name, 
                f'探索{culture_name}的丰富文化遗产和艺术珍品。')
            # 规范化图片路径
            if culture.get('representative_image'):
                culture['representative_image'] = normalize_image_path(culture['representative_image'])
        
        cursor.close()
        conn.close()
        
        return render_template('browse.html', cultures=cultures)
    except Error as e:
        if conn:
            conn.close()
        return render_template('error.html', 
                             error_message=f"数据库查询错误: {str(e)}"), 500

@app.route('/culture/<int:culture_id>')
def culture_detail(culture_id):
    """
    某个文化的文物目录页面：显示该文化下的所有文物
    """
    conn = get_db_connection()
    if conn is None:
        return render_template('error.html', 
                             error_message="无法连接到数据库。请检查数据库配置和连接状态。"), 500
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        # 获取文化列表并找到对应的文化名称（使用与browse_cultures相同的排序方式）
        culture_list_query = """
            SELECT 
                p.Culture AS culture_name,
                COUNT(DISTINCT a.Artifact_PK) AS artifact_count
            FROM PROPERTIES p
            LEFT JOIN ARTIFACTS a ON p.Artifact_PK = a.Artifact_PK
            WHERE p.Culture IS NOT NULL AND p.Culture != ''
            GROUP BY p.Culture
            HAVING artifact_count > 0
            ORDER BY artifact_count DESC, p.Culture
        """
        cursor.execute(culture_list_query)
        all_cultures = cursor.fetchall()
        
        # 根据culture_id找到对应的文化名称（culture_id现在是索引，需与browse_cultures保持一致）
        culture = None
        culture_name = None
        try:
            culture_idx = int(culture_id) - 1
            if 0 <= culture_idx < len(all_cultures):
                culture_name = all_cultures[culture_idx]['culture_name']
                culture = {'culture_id': culture_id, 'culture_name': culture_name}
        except (ValueError, IndexError):
            pass
        
        if not culture or not culture_name:
            cursor.close()
            conn.close()
            abort(404)
        
        # 构建该文化下的文物列表查询
        query = """
            SELECT 
                a.Artifact_PK AS artifact_id,
                a.Title_CN AS title,
                a.Date_CN AS date_text,
                ANY_VALUE(iv.Local_Path) AS local_path
            FROM ARTIFACTS a
            LEFT JOIN PROPERTIES p ON a.Artifact_PK = p.Artifact_PK
            LEFT JOIN IMAGE_VERSIONS iv ON a.Artifact_PK = iv.Artifact_PK
            WHERE p.Culture = %s
            GROUP BY a.Artifact_PK
            ORDER BY a.Artifact_PK DESC
        """
        cursor.execute(query, (culture_name,))
        artifacts = cursor.fetchall()
        
        # 规范化图片路径
        for artifact in artifacts:
            if artifact.get('local_path'):
                artifact['local_path'] = normalize_image_path(artifact['local_path'])
        
        cursor.close()
        conn.close()
        
        return render_template('culture_detail.html', culture=culture, artifacts=artifacts)
    except Error as e:
        if conn:
            conn.close()
        return render_template('error.html', 
                             error_message=f"数据库查询错误: {str(e)}"), 500

@app.route('/geographies')
@app.route('/browse_geographies')
def browse_geographies():
    """
    空间浏览页面：显示所有地理分类
    每个地理区域显示名称、文物数量、代表性图片和描述
    """
    conn = get_db_connection()
    if conn is None:
        return render_template('error.html', 
                             error_message="无法连接到数据库。请检查数据库配置和连接状态。"), 500
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        # 构建地理浏览查询（从PROPERTIES表获取地理信息）
        query = """
            SELECT 
                p.Geography AS geography_name,
                COUNT(DISTINCT a.Artifact_PK) AS artifact_count,
                ANY_VALUE(iv.Local_Path) AS representative_image
            FROM PROPERTIES p
            LEFT JOIN ARTIFACTS a ON p.Artifact_PK = a.Artifact_PK
            LEFT JOIN IMAGE_VERSIONS iv ON a.Artifact_PK = iv.Artifact_PK
            WHERE p.Geography IS NOT NULL AND p.Geography != ''
            GROUP BY p.Geography
            HAVING artifact_count > 0
            ORDER BY artifact_count DESC, p.Geography
        """
        cursor.execute(query)
        geographies_raw = cursor.fetchall()
        
        # 转换数据格式，添加geography_id
        geographies = []
        for idx, geography in enumerate(geographies_raw, 1):
            geography_dict = {
                'geography_id': idx,
                'geography_name': geography['geography_name'],
                'artifact_count': geography['artifact_count'],
                'representative_image': geography['representative_image']
            }
            geographies.append(geography_dict)
        
        # 为每个地理区域添加描述和规范化图片路径
        for geography in geographies:
            geography_name = geography.get('geography_name', '')
            # 添加描述
            geography['description'] = f'探索{geography_name}地区的丰富文化遗产和艺术珍品。'
            # 规范化图片路径
            if geography.get('representative_image'):
                geography['representative_image'] = normalize_image_path(geography['representative_image'])
        
        cursor.close()
        conn.close()
        
        return render_template('browse_geographies.html', geographies=geographies)
    except Error as e:
        if conn:
            conn.close()
        return render_template('error.html', 
                             error_message=f"数据库查询错误: {str(e)}"), 500

@app.route('/geography/<int:geography_id>')
def geography_detail(geography_id):
    """
    某个地理区域的文物目录页面：显示该地理区域下的所有文物
    """
    conn = get_db_connection()
    if conn is None:
        return render_template('error.html', 
                             error_message="无法连接到数据库。请检查数据库配置和连接状态。"), 500
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        # 获取地理列表并找到对应的地理名称（使用与browse_geographies相同的排序方式）
        geography_list_query = """
            SELECT 
                p.Geography AS geography_name,
                COUNT(DISTINCT a.Artifact_PK) AS artifact_count
            FROM PROPERTIES p
            LEFT JOIN ARTIFACTS a ON p.Artifact_PK = a.Artifact_PK
            WHERE p.Geography IS NOT NULL AND p.Geography != ''
            GROUP BY p.Geography
            HAVING artifact_count > 0
            ORDER BY artifact_count DESC, p.Geography
        """
        cursor.execute(geography_list_query)
        all_geographies = cursor.fetchall()
        
        # 根据geography_id找到对应的地理名称（geography_id现在是索引，需与browse_geographies保持一致）
        geography = None
        geography_name = None
        try:
            geography_idx = int(geography_id) - 1
            if 0 <= geography_idx < len(all_geographies):
                geography_name = all_geographies[geography_idx]['geography_name']
                geography = {'geography_id': geography_id, 'geography_name': geography_name}
        except (ValueError, IndexError):
            pass
        
        if not geography or not geography_name:
            cursor.close()
            conn.close()
            abort(404)
        
        # 构建该地理区域下的文物列表查询
        query = """
            SELECT 
                a.Artifact_PK AS artifact_id,
                a.Title_CN AS title,
                a.Date_CN AS date_text,
                ANY_VALUE(iv.Local_Path) AS local_path
            FROM ARTIFACTS a
            LEFT JOIN PROPERTIES p ON a.Artifact_PK = p.Artifact_PK
            LEFT JOIN IMAGE_VERSIONS iv ON a.Artifact_PK = iv.Artifact_PK
            WHERE p.Geography = %s
            GROUP BY a.Artifact_PK
            ORDER BY a.Artifact_PK DESC
        """
        cursor.execute(query, (geography_name,))
        artifacts = cursor.fetchall()
        
        # 规范化图片路径
        for artifact in artifacts:
            if artifact.get('local_path'):
                artifact['local_path'] = normalize_image_path(artifact['local_path'])
        
        cursor.close()
        conn.close()
        
        return render_template('geography_detail.html', geography=geography, artifacts=artifacts)
    except Error as e:
        if conn:
            conn.close()
        return render_template('error.html', 
                             error_message=f"数据库查询错误: {str(e)}"), 500

# ========== 用户认证相关函数 ==========

def init_user_tables():
    """初始化用户相关表（如果不存在）"""
    conn = get_db_connection()
    if conn is None:
        return False
    
    try:
        cursor = conn.cursor()
        
        # 创建用户表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Users (
                user_id INT AUTO_INCREMENT PRIMARY KEY,
                email VARCHAR(255) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                username VARCHAR(100),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                collection_count INT DEFAULT 0
            )
        """)
        
        # 创建图集表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Albums (
                album_id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                name VARCHAR(255) NOT NULL,
                is_public BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE
            )
        """)
        
        # 创建收藏表（图集与文物的关联）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Collections (
                collection_id INT AUTO_INCREMENT PRIMARY KEY,
                album_id INT NOT NULL,
                artifact_id INT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (album_id) REFERENCES Albums(album_id) ON DELETE CASCADE
            )
        """)
        
        # 创建导出记录表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ExportRecords (
                export_id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                album_id INT,
                description VARCHAR(500),
                format VARCHAR(50),
                status VARCHAR(50) DEFAULT '处理中',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE,
                FOREIGN KEY (album_id) REFERENCES Albums(album_id) ON DELETE SET NULL
            )
        """)
        
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Error as e:
        print(f"Error initializing user tables: {e}")
        if conn:
            conn.close()
        return False

def validate_email(email):
    """验证邮箱格式"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def get_user_by_email(email):
    """根据邮箱获取用户"""
    conn = get_db_connection()
    if conn is None:
        return None
    
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM Users WHERE email = %s", (email,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        return user
    except Error as e:
        print(f"Error getting user: {e}")
        if conn:
            conn.close()
        return None

def create_user(email, password, username=None):
    """创建新用户"""
    conn = get_db_connection()
    if conn is None:
        return None
    
    try:
        cursor = conn.cursor()
        password_hash = generate_password_hash(password)
        if username is None:
            username = email.split('@')[0]  # 默认用户名为邮箱前缀
        
        cursor.execute("""
            INSERT INTO Users (email, password_hash, username)
            VALUES (%s, %s, %s)
        """, (email, password_hash, username))
        
        user_id = cursor.lastrowid
        conn.commit()
        cursor.close()
        conn.close()
        return user_id
    except Error as e:
        print(f"Error creating user: {e}")
        if conn:
            conn.rollback()
            conn.close()
        return None

def get_user_albums(user_id):
    """获取用户的图集列表，包含封面图片"""
    conn = get_db_connection()
    if conn is None:
        return []
    
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT a.*, 
                   COUNT(DISTINCT c.collection_id) as item_count,
                   (SELECT iv.Local_Path 
                    FROM Collections c2
                    INNER JOIN ARTIFACTS art ON c2.artifact_id = art.Artifact_PK
                    LEFT JOIN IMAGE_VERSIONS iv ON art.Artifact_PK = iv.Artifact_PK
                    WHERE c2.album_id = a.album_id 
                      AND iv.Local_Path IS NOT NULL 
                      AND iv.Local_Path != ''
                    ORDER BY c2.created_at DESC
                    LIMIT 1) as cover_image
            FROM Albums a
            LEFT JOIN Collections c ON a.album_id = c.album_id
            WHERE a.user_id = %s
            GROUP BY a.album_id
            ORDER BY a.created_at DESC
        """, (user_id,))
        albums = cursor.fetchall()
        
        # 规范化封面图片路径
        for album in albums:
            if album.get('cover_image'):
                album['cover_image'] = normalize_image_path(album['cover_image'])
        
        cursor.close()
        conn.close()
        return albums
    except Error as e:
        print(f"Error getting albums: {e}")
        if conn:
            conn.close()
        return []


def get_user_collection_stats(user_id):
    """获取用户收藏统计信息（虚拟数据用于演示）"""
    # 这里返回虚拟数据，实际应该从数据库查询
    return {
        'total_count': 234,
        'era_distribution': {
            '商周时期': 60,
            '秦汉时期': 25,
            '唐宋时期': 15
        },
        'material_composition': {
            '青铜': 70,
            '玉器': 20,
            '其他': 10
        }
    }

def get_export_records(user_id):
    """获取用户的导出记录"""
    conn = get_db_connection()
    if conn is None:
        return []
    
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT er.*, a.name as album_name
            FROM ExportRecords er
            LEFT JOIN Albums a ON er.album_id = a.album_id
            WHERE er.user_id = %s
            ORDER BY er.created_at DESC
            LIMIT 10
        """, (user_id,))
        records = cursor.fetchall()
        cursor.close()
        conn.close()
        return records
    except Error as e:
        print(f"Error getting export records: {e}")
        if conn:
            conn.close()
        return []

def create_album(user_id, name, is_public=True):
    """创建新图集"""
    conn = get_db_connection()
    if conn is None:
        return None
    
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO Albums (user_id, name, is_public)
            VALUES (%s, %s, %s)
        """, (user_id, name, is_public))
        
        album_id = cursor.lastrowid
        conn.commit()
        cursor.close()
        conn.close()
        return album_id
    except Error as e:
        print(f"Error creating album: {e}")
        if conn:
            conn.rollback()
            conn.close()
        return None

def get_default_album(user_id):
    """获取或创建用户的默认图集"""
    conn = get_db_connection()
    if conn is None:
        return None
    
    try:
        cursor = conn.cursor(dictionary=True)
        # 先查找是否已有默认收藏夹
        cursor.execute("""
            SELECT album_id FROM Albums 
            WHERE user_id = %s AND name = '默认收藏夹'
            LIMIT 1
        """, (user_id,))
        album = cursor.fetchone()
        
        if album:
            album_id = album['album_id']
        else:
            # 创建默认收藏夹
            cursor.execute("""
                INSERT INTO Albums (user_id, name, is_public)
                VALUES (%s, '默认收藏夹', TRUE)
            """, (user_id,))
            album_id = cursor.lastrowid
            conn.commit()
        
        cursor.close()
        conn.close()
        return album_id
    except Error as e:
        print(f"Error getting default album: {e}")
        if conn:
            conn.rollback()
            conn.close()
        return None

def add_artifact_to_album(album_id, artifact_id):
    """添加文物到图集（如果已存在则不重复添加）"""
    conn = get_db_connection()
    if conn is None:
        print("Error: Database connection failed")
        return False
    
    try:
        # 确保类型正确
        album_id = int(album_id)
        artifact_id = int(artifact_id)
        
        cursor = conn.cursor()
        # 检查是否已存在
        cursor.execute("""
            SELECT collection_id FROM Collections 
            WHERE album_id = %s AND artifact_id = %s
            LIMIT 1
        """, (album_id, artifact_id))
        
        if cursor.fetchone():
            # 已存在，不重复添加，但返回True表示操作成功
            cursor.close()
            conn.close()
            return True
        
        # 添加新的收藏记录
        cursor.execute("""
            INSERT INTO Collections (album_id, artifact_id)
            VALUES (%s, %s)
        """, (album_id, artifact_id))
        
        conn.commit()
        cursor.close()
        conn.close()
        print(f"Successfully added artifact {artifact_id} to album {album_id}")
        return True
    except Error as e:
        print(f"Error adding artifact to album: {e}")
        print(f"Album ID: {album_id}, Artifact ID: {artifact_id}")
        import traceback
        traceback.print_exc()
        if conn:
            conn.rollback()
            conn.close()
        return False
    except Exception as e:
        print(f"Unexpected error adding artifact to album: {e}")
        import traceback
        traceback.print_exc()
        if conn:
            conn.close()
        return False



def get_album_artifacts(album_id):
    """获取图集中的所有文物"""
    conn = get_db_connection()
    if conn is None:
        return []
    
    try:
        cursor = conn.cursor(dictionary=True)
        # 修复GROUP BY错误：将created_at添加到GROUP BY或使用MIN/MAX
        cursor.execute("""
            SELECT 
                a.Artifact_PK AS artifact_id,
                a.Title_CN AS title,
                a.Date_CN AS date_text,
                ANY_VALUE(iv.Local_Path) AS local_path,
                MIN(c.created_at) AS created_at
            FROM Collections c
            INNER JOIN ARTIFACTS a ON c.artifact_id = a.Artifact_PK
            LEFT JOIN IMAGE_VERSIONS iv ON a.Artifact_PK = iv.Artifact_PK
            WHERE c.album_id = %s
            GROUP BY a.Artifact_PK, a.Title_CN, a.Date_CN
            ORDER BY MIN(c.created_at) ASC
        """, (album_id,))
        artifacts = cursor.fetchall()
        
        # 规范化图片路径
        for artifact in artifacts:
            if artifact.get('local_path'):
                artifact['local_path'] = normalize_image_path(artifact['local_path'])
        
        cursor.close()
        conn.close()
        return artifacts
    except Error as e:
        print(f"Error getting album artifacts: {e}")
        print(f"Album ID: {album_id}, Error: {str(e)}")
        if conn:
            conn.close()
        return []

# ========== 用户认证路由 ==========

@app.route('/register', methods=['GET', 'POST'])
def register():
    """用户注册"""
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        username = request.form.get('username', '').strip()
        
        # 验证输入
        if not email or not password:
            flash('邮箱和密码不能为空', 'error')
            return redirect(url_for('user_center'))
        
        if not validate_email(email):
            flash('邮箱格式不正确', 'error')
            return redirect(url_for('user_center'))
        
        if len(password) < 6:
            flash('密码长度至少为6位', 'error')
            return redirect(url_for('user_center'))
        
        # 检查用户是否已存在
        if get_user_by_email(email):
            flash('该邮箱已被注册', 'error')
            return redirect(url_for('user_center'))
        
        # 创建用户
        user_id = create_user(email, password, username if username else None)
        if user_id:
            session['user_id'] = user_id
            session['email'] = email
            session['username'] = username if username else email.split('@')[0]
            flash('注册成功！', 'success')
            return redirect(url_for('user_center'))
        else:
            flash('注册失败，请稍后重试', 'error')
            return redirect(url_for('user_center'))
    
    return redirect(url_for('user_center'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    """用户登录"""
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        
        if not email or not password:
            flash('邮箱和密码不能为空', 'error')
            return redirect(url_for('user_center'))
        
        user = get_user_by_email(email)
        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['user_id']
            session['email'] = user['email']
            session['username'] = user.get('username') or email.split('@')[0]
            flash('登录成功！', 'success')
            return redirect(url_for('user_center'))
        else:
            flash('邮箱或密码错误', 'error')
            return redirect(url_for('user_center'))
    
    return redirect(url_for('user_center'))

@app.route('/logout')
def logout():
    """用户登出"""
    session.clear()
    flash('已退出登录', 'info')
    return redirect(url_for('user_center'))

# ========== 图集相关API路由 ==========

@app.route('/api/albums', methods=['GET'])
def get_albums_api():
    """获取当前用户的图集列表（JSON格式，用于添加到图集时的选择）"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'albums': []})
    
    albums = get_user_albums(user_id)
    return jsonify({'albums': [{'album_id': a['album_id'], 'name': a['name']} for a in albums]})

@app.route('/api/album/create', methods=['POST'])
def create_album_api():
    """创建新图集（API）"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'message': '请先登录'}), 401
    
    data = request.get_json()
    album_name = data.get('name', '').strip()
    is_public = data.get('is_public', True)
    
    if not album_name:
        return jsonify({'success': False, 'message': '图集名称不能为空'}), 400
    
    album_id = create_album(user_id, album_name, is_public)
    if album_id:
        return jsonify({'success': True, 'album_id': album_id, 'message': '图集创建成功'})
    else:
        return jsonify({'success': False, 'message': '创建图集失败'}), 500


@app.route('/api/artifact/add_to_album', methods=['POST'])
def add_to_album_api():
    """添加文物到图集"""
    # 确保用户表已初始化
    init_user_tables()
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': '请求数据无效'}), 400
        
        artifact_id = data.get('artifact_id')
        album_id = data.get('album_id')
        album_name = data.get('album_name') or ''
        album_name = album_name.strip() if album_name else ''  # 用于创建新图集
        
        # 转换artifact_id为整数
        try:
            artifact_id = int(artifact_id) if artifact_id else None
        except (ValueError, TypeError):
            return jsonify({'success': False, 'message': '文物ID格式错误'}), 400
        
        if not artifact_id:
            return jsonify({'success': False, 'message': '文物ID不能为空'}), 400
        
        # 验证文物是否存在
        conn = get_db_connection()
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT Artifact_PK FROM ARTIFACTS WHERE Artifact_PK = %s", (artifact_id,))
                if not cursor.fetchone():
                    cursor.close()
                    conn.close()
                    return jsonify({'success': False, 'message': '文物不存在'}), 404
                cursor.close()
                conn.close()
            except Exception as e:
                print(f"Error checking artifact: {e}")
                if conn:
                    conn.close()
        
        user_id = session.get('user_id')
        
        # 如果未登录，使用session存储
        if not user_id:
            # 未登录用户：使用session存储默认收藏夹
            if 'guest_collections' not in session:
                session['guest_collections'] = []
            
            # 检查是否已存在
            if artifact_id not in session['guest_collections']:
                session['guest_collections'].append(artifact_id)
                session.modified = True
                return jsonify({'success': True, 'message': '已添加到默认收藏夹'})
            else:
                return jsonify({'success': True, 'message': '该文物已在收藏夹中'})
        
        # 已登录用户
        if album_name:
            # 创建新图集
            album_id = create_album(user_id, album_name)
            if not album_id:
                return jsonify({'success': False, 'message': '创建图集失败'}), 500
        
        # 转换album_id为整数（如果存在）
        if album_id:
            try:
                album_id = int(album_id)
            except (ValueError, TypeError):
                album_id = None
        
        if not album_id:
            # 如果没有指定图集，使用默认收藏夹
            album_id = get_default_album(user_id)
            if not album_id:
                return jsonify({'success': False, 'message': '获取默认图集失败'}), 500
        
        # 验证图集属于当前用户
        albums = get_user_albums(user_id)
        if not any(a['album_id'] == album_id for a in albums):
            return jsonify({'success': False, 'message': '无权访问该图集'}), 403
        
        # 添加文物到图集
        if add_artifact_to_album(album_id, artifact_id):
            return jsonify({'success': True, 'message': '已添加到图集'})
        else:
            return jsonify({'success': False, 'message': '添加失败，请检查数据库连接'}), 500
            
    except Exception as e:
        print(f"Error in add_to_album_api: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'添加失败: {str(e)}'}), 500

@app.route('/api/album/delete', methods=['POST'])
def delete_album_api():
    """删除图集"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'message': '请先登录'}), 401
    
    data = request.get_json()
    album_id = data.get('album_id')
    
    if not album_id:
        return jsonify({'success': False, 'message': '图集ID不能为空'}), 400
    
    try:
        album_id = int(album_id)
    except (ValueError, TypeError):
        return jsonify({'success': False, 'message': '图集ID格式错误'}), 400
    
    # 验证图集属于当前用户
    albums = get_user_albums(user_id)
    album = next((a for a in albums if a['album_id'] == album_id), None)
    
    if not album:
        return jsonify({'success': False, 'message': '图集不存在或无权限'}), 403
    
    # 不能删除默认收藏夹
    if album['name'] == '默认收藏夹':
        return jsonify({'success': False, 'message': '不能删除默认收藏夹'}), 400
    
    # 删除图集（外键约束会自动删除相关的Collections记录）
    conn = get_db_connection()
    if conn is None:
        return jsonify({'success': False, 'message': '数据库连接失败'}), 500
    
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Albums WHERE album_id = %s AND user_id = %s", (album_id, user_id))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({'success': True, 'message': '图集已删除'})
    except Error as e:
        print(f"Error deleting album: {e}")
        if conn:
            conn.rollback()
            conn.close()
        return jsonify({'success': False, 'message': '删除失败'}), 500

@app.route('/api/album/rename', methods=['POST'])
def rename_album_api():
    """重命名图集"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'message': '请先登录'}), 401
    
    data = request.get_json()
    album_id = data.get('album_id')
    new_name = data.get('name', '').strip()
    
    if not album_id:
        return jsonify({'success': False, 'message': '图集ID不能为空'}), 400
    
    if not new_name:
        return jsonify({'success': False, 'message': '图集名称不能为空'}), 400
    
    try:
        album_id = int(album_id)
    except (ValueError, TypeError):
        return jsonify({'success': False, 'message': '图集ID格式错误'}), 400
    
    # 验证图集属于当前用户
    albums = get_user_albums(user_id)
    album = next((a for a in albums if a['album_id'] == album_id), None)
    
    if not album:
        return jsonify({'success': False, 'message': '图集不存在或无权限'}), 403
    
    # 更新图集名称
    conn = get_db_connection()
    if conn is None:
        return jsonify({'success': False, 'message': '数据库连接失败'}), 500
    
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE Albums SET name = %s WHERE album_id = %s AND user_id = %s", 
                      (new_name, album_id, user_id))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({'success': True, 'message': '图集已重命名'})
    except Error as e:
        print(f"Error renaming album: {e}")
        if conn:
            conn.rollback()
            conn.close()
        return jsonify({'success': False, 'message': '重命名失败'}), 500

@app.route('/api/album/remove_artifact', methods=['POST'])
def remove_artifact_from_album_api():
    """从图集中删除文物"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'message': '请先登录'}), 401
    
    data = request.get_json()
    album_id = data.get('album_id')
    artifact_id = data.get('artifact_id')
    
    if not album_id or not artifact_id:
        return jsonify({'success': False, 'message': '图集ID和文物ID不能为空'}), 400
    
    try:
        album_id = int(album_id)
        artifact_id = int(artifact_id)
    except (ValueError, TypeError):
        return jsonify({'success': False, 'message': 'ID格式错误'}), 400
    
    # 验证图集属于当前用户
    albums = get_user_albums(user_id)
    if not any(a['album_id'] == album_id for a in albums):
        return jsonify({'success': False, 'message': '无权访问该图集'}), 403
    
    # 删除收藏记录
    conn = get_db_connection()
    if conn is None:
        return jsonify({'success': False, 'message': '数据库连接失败'}), 500
    
    try:
        cursor = conn.cursor()
        cursor.execute("""
            DELETE FROM Collections 
            WHERE album_id = %s AND artifact_id = %s
        """, (album_id, artifact_id))
        conn.commit()
        affected_rows = cursor.rowcount
        cursor.close()
        conn.close()
        
        if affected_rows > 0:
            return jsonify({'success': True, 'message': '已从图集中移除'})
        else:
            return jsonify({'success': False, 'message': '该文物不在图集中'}), 404
    except Error as e:
        print(f"Error removing artifact from album: {e}")
        if conn:
            conn.rollback()
            conn.close()
        return jsonify({'success': False, 'message': '删除失败'}), 500

# ========== 用户中心路由 ==========

@app.route('/user')
@app.route('/user_center')
def user_center():
    """用户中心页面"""
    # 初始化用户表（如果不存在）
    init_user_tables()
    
    user_id = session.get('user_id')
    
    if user_id:
        # 已登录用户 - 获取用户信息
        user = get_user_by_email(session.get('email'))
        if not user:
            session.clear()
            return render_template('user_center.html', is_logged_in=False)
        
        # 获取用户图集
        albums = get_user_albums(user_id)
        
        # 确保有默认收藏夹
        has_default = any(a['name'] == '默认收藏夹' for a in albums)
        if not has_default:
            get_default_album(user_id)
            albums = get_user_albums(user_id)
        
        # 获取收藏统计（虚拟数据）
        stats = get_user_collection_stats(user_id)
        
        # 获取导出记录
        export_records = get_export_records(user_id)
        
        # 如果没有导出记录，创建一些虚拟记录用于演示
        if not export_records:
            export_records = [
                {
                    'created_at': '2025-12-04 14:30',
                    'description': '商周青铜器研究 - 完整元数据',
                    'format': 'CSV',
                    'status': '已完成',
                    'album_name': '商周青铜器研究'
                },
                {
                    'created_at': '2025-12-03 09:15',
                    'description': '默认收藏夹 - 图像包(高才)',
                    'format': 'ZIP',
                    'status': '已完成',
                    'album_name': '默认收藏夹'
                },
                {
                    'created_at': '2025-12-03 09:10',
                    'description': '纹样灵感 - 报告',
                    'format': 'PDF',
                    'status': '处理中',
                    'album_name': '纹样灵感'
                }
            ]
        
        # 确保有默认收藏夹（已经在上面处理了，这里只是备用）
        # 如果没有图集，创建默认收藏夹
        if not albums:
            get_default_album(user_id)
            albums = get_user_albums(user_id)
        
        return render_template('user_center.html', 
                             is_logged_in=True,
                             user=user,
                             albums=albums,
                             stats=stats,
                             export_records=export_records,
                             page_view='dashboard')  # 默认显示dashboard视图
    else:
        # 未登录用户 - 显示访客模式
        # 获取session中的收藏
        guest_collections = session.get('guest_collections', [])
        
        # 获取封面图片（第一张图片）
        cover_image = None
        if guest_collections:
            conn = get_db_connection()
            if conn:
                try:
                    cursor = conn.cursor(dictionary=True)
                    cursor.execute("""
                        SELECT iv.Local_Path 
                        FROM ARTIFACTS a
                        LEFT JOIN IMAGE_VERSIONS iv ON a.Artifact_PK = iv.Artifact_PK
                        WHERE a.Artifact_PK = %s 
                          AND iv.Local_Path IS NOT NULL 
                          AND iv.Local_Path != ''
                        LIMIT 1
                    """, (guest_collections[0],))
                    result = cursor.fetchone()
                    if result:
                        cover_image = normalize_image_path(result['Local_Path'])
                    cursor.close()
                    conn.close()
                except Error as e:
                    print(f"Error getting guest cover: {e}")
                    if conn:
                        conn.close()
        
        guest_albums = [{
            'album_id': 'guest_default',
            'name': '默认收藏夹',
            'is_public': True,
            'item_count': len(guest_collections),
            'cover_image': cover_image
        }]
        return render_template('user_center.html', 
                             is_logged_in=False,
                             albums=guest_albums)

@app.route('/album/<int:album_id>')
def album_detail(album_id):
    """显示图集详情（已登录用户）"""
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('user_center'))
    
    # 验证图集属于当前用户
    albums = get_user_albums(user_id)
    album = next((a for a in albums if a['album_id'] == album_id), None)
    
    if not album:
        abort(404)
    
    # 获取图集中的文物
    artifacts = get_album_artifacts(album_id)
    
    return render_template('album_detail.html', album=album, artifacts=artifacts)


@app.route('/album/guest')
def guest_album_detail():
    """显示访客默认收藏夹"""
    guest_collections = session.get('guest_collections', [])
    
    if not guest_collections:
        # 如果没有收藏，返回空列表
        artifacts = []
    else:
        # 获取文物信息
        conn = get_db_connection()
        if conn is None:
            artifacts = []
        else:
            try:
                cursor = conn.cursor(dictionary=True)
                placeholders = ','.join(['%s'] * len(guest_collections))
                query = f"""
                    SELECT 
                        a.Artifact_PK AS artifact_id,
                        a.Title_CN AS title,
                        a.Date_CN AS date_text,
                        ANY_VALUE(iv.Local_Path) AS local_path
                    FROM ARTIFACTS a
                    LEFT JOIN IMAGE_VERSIONS iv ON a.Artifact_PK = iv.Artifact_PK
                    WHERE a.Artifact_PK IN ({placeholders})
                    GROUP BY a.Artifact_PK
                    ORDER BY a.Artifact_PK DESC
                """
                cursor.execute(query, guest_collections)
                artifacts = cursor.fetchall()
                
                # 规范化图片路径
                for artifact in artifacts:
                    if artifact.get('local_path'):
                        artifact['local_path'] = normalize_image_path(artifact['local_path'])
                
                cursor.close()
                conn.close()
            except Error as e:
                print(f"Error getting guest artifacts: {e}")
                artifacts = []
    
    album = {
        'album_id': 'guest_default',
        'name': '默认收藏夹',
        'is_public': True,
        'item_count': len(artifacts)
    }
    
    return render_template('album_detail.html', album=album, artifacts=artifacts)

@app.route('/support')
def support():
    """平台支持页面"""
    return render_template('support.html')

@app.route('/user/collections')
def user_collections():
    """用户图集页面（已登录页面2）"""
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('user_center'))
    
    user = get_user_by_email(session.get('email'))
    if not user:
        session.clear()
        return redirect(url_for('user_center'))
    
    albums = get_user_albums(user_id)
    
    # 确保有默认收藏夹
    has_default = any(a['name'] == '默认收藏夹' for a in albums)
    if not has_default:
        get_default_album(user_id)
        albums = get_user_albums(user_id)
    
    export_records = get_export_records(user_id)
    stats = get_user_collection_stats(user_id)  # 添加stats用于模板
    
    # 如果没有导出记录，创建虚拟记录
    if not export_records:
        export_records = [
            {
                'created_at': '2025-12-04 14:30',
                'description': '商周青铜器研究 - 完整元数据',
                'format': 'CSV',
                'status': '已完成',
                'album_name': '商周青铜器研究'
            },
            {
                'created_at': '2025-12-03 09:15',
                'description': '默认收藏夹 - 图像包(高才)',
                'format': 'ZIP',
                'status': '已完成',
                'album_name': '默认收藏夹'
            },
            {
                'created_at': '2025-12-03 09:10',
                'description': '纹样灵感 - 报告',
                'format': 'PDF',
                'status': '处理中',
                'album_name': '纹样灵感'
            }
        ]
    
    # 如果没有图集，创建默认图集
    if not albums:
        albums = [
            {
                'album_id': 1,
                'name': '默认收藏夹',
                'is_public': True,
                'item_count': 12
            },
            {
                'album_id': 2,
                'name': '商周青铜器研究',
                'is_public': False,
                'item_count': 58
            },
            {
                'album_id': 3,
                'name': '纹样灵感',
                'is_public': False,
                'item_count': 5
            }
        ]
    
    return render_template('user_center.html',
                         is_logged_in=True,
                         user=user,
                         albums=albums,
                         stats=stats,
                         export_records=export_records,
                         page_view='collections')


# ========== 管理员认证装饰器 ==========

ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'admin123')  # 建议使用环境变量

def admin_required(f):
    """管理员权限验证装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('is_admin'):
            flash('请先进行管理员登录', 'error')
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

# ========== 管理员认证路由 ==========

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    """管理员登录页面"""
    if request.method == 'POST':
        password = request.form.get('password', '')
        
        if password == ADMIN_PASSWORD:
            session['is_admin'] = True
            session['admin_login_time'] = datetime.now().isoformat()
            flash('管理员登录成功', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('管理员密码错误', 'error')
            return redirect(url_for('admin_login'))
    
    return render_template('admin_login.html')

@app.route('/admin/logout')
def admin_logout():
    """管理员登出"""
    session.pop('is_admin', None)
    session.pop('admin_login_time', None)
    flash('已退出管理员模式', 'info')
    return redirect(url_for('homepage'))

# ========== 管理员仪表板 ==========

@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    """管理员仪表板 - 主页"""
    conn = get_db_connection()
    if conn is None:
        return render_template('error.html', 
                             error_message="无法连接到数据库"), 500
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        # 获取统计信息
        stats = {}
        
        # 文物总数
        cursor.execute("SELECT COUNT(*) as count FROM ARTIFACTS")
        stats['total_artifacts'] = cursor.fetchone()['count']
        
        # 图片总数
        cursor.execute("SELECT COUNT(*) as count FROM IMAGE_VERSIONS")
        stats['total_images'] = cursor.fetchone()['count']
        
        # 来源机构数
        cursor.execute("SELECT COUNT(*) as count FROM SOURCES")
        stats['total_sources'] = cursor.fetchone()['count']
        
        # 最近7天新增文物
        cursor.execute("""
            SELECT COUNT(*) as count FROM LOGS 
            WHERE Table_Name = 'ARTIFACTS' 
            AND Operation_Type = 'INSERT' 
            AND Log_Time >= DATE_SUB(NOW(), INTERVAL 7 DAY)
        """)
        result = cursor.fetchone()
        stats['recent_artifacts'] = result['count'] if result else 0
        
        # 最近操作日志（前10条）
        cursor.execute("""
            SELECT Log_PK, Log_Time, Table_Name, Operation_Type, 
                   User_ID, Status, Description
            FROM LOGS
            ORDER BY Log_Time DESC
            LIMIT 10
        """)
        recent_logs = cursor.fetchall()
        
        # 按来源机构统计文物数量
        cursor.execute("""
            SELECT s.Museum_Name_CN, COUNT(a.Artifact_PK) as count
            FROM SOURCES s
            LEFT JOIN ARTIFACTS a ON s.Source_ID = a.Source_ID
            GROUP BY s.Source_ID
            ORDER BY count DESC
        """)
        source_stats = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return render_template('admin_dashboard.html', 
                             stats=stats,
                             recent_logs=recent_logs,
                             source_stats=source_stats)
    except Error as e:
        if conn:
            conn.close()
        return render_template('error.html', 
                             error_message=f"数据库查询错误: {str(e)}"), 500

# ========== 元数据导入功能 ==========

ALLOWED_EXTENSIONS = {'csv', 'xlsx', 'xls'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/admin/import', methods=['GET', 'POST'])
@admin_required
def admin_import():
    """元数据导入页面"""
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('没有上传文件', 'error')
            return redirect(request.url)
        
        file = request.files['file']
        if file.filename == '':
            flash('未选择文件', 'error')
            return redirect(request.url)
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            
            # 读取文件
            try:
                if filename.endswith('.csv'):
                    df = pd.read_csv(file, encoding='utf-8')
                else:
                    df = pd.read_excel(file)
                
                # 验证必需列
                required_columns = ['Title_CN', 'Source_ID', 'Original_ID']
                missing_columns = [col for col in required_columns if col not in df.columns]
                if missing_columns:
                    flash(f'缺少必需列: {", ".join(missing_columns)}', 'error')
                    return redirect(request.url)
                
                # 导入数据
                import_mode = request.form.get('import_mode', 'skip')  # skip/update
                result = import_artifacts_from_dataframe(df, import_mode)
                
                flash(f'导入成功：新增 {result["inserted"]} 条，更新 {result["updated"]} 条，跳过 {result["skipped"]} 条', 'success')
                return redirect(url_for('admin_dashboard'))
                
            except Exception as e:
                flash(f'导入失败: {str(e)}', 'error')
                return redirect(request.url)
        else:
            flash('不支持的文件格式，请上传 CSV 或 Excel 文件', 'error')
            return redirect(request.url)
    
    return render_template('admin_import.html')

def import_artifacts_from_dataframe(df, import_mode='skip'):
    """从DataFrame导入文物数据"""
    conn = get_db_connection()
    if conn is None:
        raise Exception("无法连接到数据库")
    
    result = {'inserted': 0, 'updated': 0, 'skipped': 0, 'errors': []}
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        for index, row in df.iterrows():
            try:
                # 检查是否已存在（根据 Source_ID + Original_ID）
                cursor.execute("""
                    SELECT Artifact_PK FROM ARTIFACTS 
                    WHERE Source_ID = %s AND Original_ID = %s
                """, (row['Source_ID'], row['Original_ID']))
                
                existing = cursor.fetchone()
                
                if existing:
                    if import_mode == 'update':
                        # 更新模式
                        update_artifact(cursor, existing['Artifact_PK'], row)
                        result['updated'] += 1
                    else:
                        # 跳过模式
                        result['skipped'] += 1
                else:
                    # 插入新记录
                    insert_artifact(cursor, row)
                    result['inserted'] += 1
                
                conn.commit()
                
            except Exception as e:
                result['errors'].append(f"行 {index + 2}: {str(e)}")
                conn.rollback()
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        if conn:
            conn.close()
        raise e
    
    return result

def insert_artifact(cursor, row):
    """插入新文物记录"""
    # 插入主表
    cursor.execute("""
        INSERT INTO ARTIFACTS (
            Source_ID, Original_ID, Title_CN, Title_EN, 
            Description_CN, Classification, Material, 
            Date_CN, Date_EN, Start_Year, End_Year
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        row.get('Source_ID'),
        row.get('Original_ID'),
        row.get('Title_CN'),
        row.get('Title_EN'),
        row.get('Description_CN'),
        row.get('Classification'),
        row.get('Material'),
        row.get('Date_CN'),
        row.get('Date_EN'),
        row.get('Start_Year'),
        row.get('End_Year')
    ))
    
    artifact_id = cursor.lastrowid
    
    # 插入属性表
    if any(row.get(col) for col in ['Geography', 'Culture', 'Artist', 'Credit_Line', 'Page_Link']):
        cursor.execute("""
            INSERT INTO PROPERTIES (
                Artifact_PK, Geography, Culture, Artist, 
                Credit_Line, Page_Link
            ) VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            artifact_id,
            row.get('Geography'),
            row.get('Culture'),
            row.get('Artist'),
            row.get('Credit_Line'),
            row.get('Page_Link')
        ))
    
    # 插入尺寸表（如果有）
    if row.get('Size_Type') and row.get('Size_Value'):
        cursor.execute("""
            INSERT INTO DIMENSIONS (
                Artifact_PK, Size_Type, Size_Value, Size_Unit
            ) VALUES (%s, %s, %s, %s)
        """, (
            artifact_id,
            row.get('Size_Type'),
            row.get('Size_Value'),
            row.get('Size_Unit')
        ))
    
    # 记录日志
    cursor.execute("""
        INSERT INTO LOGS (
            Artifact_PK, Table_Name, Operation_Type, 
            User_ID, Status, Description
        ) VALUES (%s, %s, %s, %s, %s, %s)
    """, (
        artifact_id,
        'ARTIFACTS',
        'INSERT',
        'admin_import',
        'Success',
        f'通过批量导入创建文物: {row.get("Title_CN")}'
    ))

def update_artifact(cursor, artifact_id, row):
    """更新文物记录"""
    cursor.execute("""
        UPDATE ARTIFACTS SET
            Title_CN = %s,
            Title_EN = %s,
            Description_CN = %s,
            Classification = %s,
            Material = %s,
            Date_CN = %s,
            Date_EN = %s,
            Start_Year = %s,
            End_Year = %s
        WHERE Artifact_PK = %s
    """, (
        row.get('Title_CN'),
        row.get('Title_EN'),
        row.get('Description_CN'),
        row.get('Classification'),
        row.get('Material'),
        row.get('Date_CN'),
        row.get('Date_EN'),
        row.get('Start_Year'),
        row.get('End_Year'),
        artifact_id
    ))
    
    # 记录日志
    cursor.execute("""
        INSERT INTO LOGS (
            Artifact_PK, Table_Name, Operation_Type, 
            User_ID, Status, Description
        ) VALUES (%s, %s, %s, %s, %s, %s)
    """, (
        artifact_id,
        'ARTIFACTS',
        'UPDATE',
        'admin_import',
        'Success',
        f'通过批量导入更新文物: {row.get("Title_CN")}'
    ))

# ========== 图像管理功能 ==========

@app.route('/admin/images')
@admin_required
def admin_images():
    """图像管理页面"""
    conn = get_db_connection()
    if conn is None:
        return render_template('error.html', 
                             error_message="无法连接到数据库"), 500
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        # 获取所有图像记录
        page = request.args.get('page', 1, type=int)
        per_page = 50
        offset = (page - 1) * per_page
        
        cursor.execute("""
            SELECT 
                iv.Version_PK,
                iv.Artifact_PK,
                a.Title_CN,
                iv.Version_Type,
                iv.Local_Path,
                iv.File_Size_KB,
                iv.Last_Processed_Time
            FROM IMAGE_VERSIONS iv
            INNER JOIN ARTIFACTS a ON iv.Artifact_PK = a.Artifact_PK
            ORDER BY iv.Last_Processed_Time DESC
            LIMIT %s OFFSET %s
        """, (per_page, offset))
        
        images = cursor.fetchall()
        
        # 获取总数
        cursor.execute("SELECT COUNT(*) as count FROM IMAGE_VERSIONS")
        total = cursor.fetchone()['count']
        
        cursor.close()
        conn.close()
        
        return render_template('admin_images.html', 
                             images=images,
                             page=page,
                             per_page=per_page,
                             total=total)
    except Error as e:
        if conn:
            conn.close()
        return render_template('error.html', 
                             error_message=f"数据库查询错误: {str(e)}"), 500

@app.route('/admin/image/replace/<int:version_id>', methods=['POST'])
@admin_required
def admin_replace_image(version_id):
    """替换图像文件"""
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': '没有上传文件'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'message': '未选择文件'}), 400
    
    conn = get_db_connection()
    if conn is None:
        return jsonify({'success': False, 'message': '数据库连接失败'}), 500
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        # 获取原图像信息
        cursor.execute("""
            SELECT Local_Path, Artifact_PK 
            FROM IMAGE_VERSIONS 
            WHERE Version_PK = %s
        """, (version_id,))
        
        old_image = cursor.fetchone()
        if not old_image:
            return jsonify({'success': False, 'message': '图像记录不存在'}), 404
        
        old_path = old_image['Local_Path']
        artifact_id = old_image['Artifact_PK']
        
        # 保存新文件（使用原文件名）
        new_filename = secure_filename(file.filename)
        new_path = old_path  # 保持路径不变，只替换文件
        
        # 确保目录存在
        file_dir = os.path.join('static', os.path.dirname(new_path))
        os.makedirs(file_dir, exist_ok=True)
        
        # 保存文件
        file.save(os.path.join('static', new_path))
        
        # 获取文件大小
        file_size_kb = os.path.getsize(os.path.join('static', new_path)) / 1024
        
        # 更新数据库记录
        cursor.execute("""
            UPDATE IMAGE_VERSIONS SET
                File_Size_KB = %s,
                Last_Processed_Time = NOW()
            WHERE Version_PK = %s
        """, (file_size_kb, version_id))
        
        # 记录替换日志
        cursor.execute("""
            INSERT INTO LOGS (
                Artifact_PK, Table_Name, Operation_Type, 
                User_ID, Status, Description
            ) VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            artifact_id,
            'IMAGE_VERSIONS',
            'IMAGE_REPLACE',
            session.get('username', 'admin'),
            'Success',
            f'图像文件替换: {old_path} -> {new_path} (版本ID: {version_id})'
        ))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({'success': True, 'message': '图像替换成功'})
        
    except Exception as e:
        if conn:
            conn.rollback()
            conn.close()
        return jsonify({'success': False, 'message': f'替换失败: {str(e)}'}), 500

# ========== 日志查看功能 ==========

@app.route('/admin/logs')
@admin_required
def admin_logs():
    """日志查看页面"""
    conn = get_db_connection()
    if conn is None:
        return render_template('error.html', 
                             error_message="无法连接到数据库"), 500
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        # 获取筛选参数
        operation_type = request.args.get('operation_type', '')
        table_name = request.args.get('table_name', '')
        date_from = request.args.get('date_from', '')
        date_to = request.args.get('date_to', '')
        
        # 构建查询
        query = """
            SELECT 
                l.Log_PK,
                l.Log_Time,
                l.Artifact_PK,
                a.Title_CN as artifact_title,
                l.Table_Name,
                l.Operation_Type,
                l.User_ID,
                l.Status,
                l.Description
            FROM LOGS l
            LEFT JOIN ARTIFACTS a ON l.Artifact_PK = a.Artifact_PK
            WHERE 1=1
        """
        params = []
        
        if operation_type:
            query += " AND l.Operation_Type = %s"
            params.append(operation_type)
        
        if table_name:
            query += " AND l.Table_Name = %s"
            params.append(table_name)
        
        if date_from:
            query += " AND DATE(l.Log_Time) >= %s"
            params.append(date_from)
        
        if date_to:
            query += " AND DATE(l.Log_Time) <= %s"
            params.append(date_to)
        
        query += " ORDER BY l.Log_Time DESC LIMIT 1000"
        
        cursor.execute(query, params)
        logs = cursor.fetchall()
        
        # 获取筛选选项
        cursor.execute("SELECT DISTINCT Operation_Type FROM LOGS ORDER BY Operation_Type")
        operation_types = [row['Operation_Type'] for row in cursor.fetchall()]
        
        cursor.execute("SELECT DISTINCT Table_Name FROM LOGS ORDER BY Table_Name")
        table_names = [row['Table_Name'] for row in cursor.fetchall()]
        
        cursor.close()
        conn.close()
        
        return render_template('admin_logs.html', 
                             logs=logs,
                             operation_types=operation_types,
                             table_names=table_names,
                             filters={
                                 'operation_type': operation_type,
                                 'table_name': table_name,
                                 'date_from': date_from,
                                 'date_to': date_to
                             })
    except Error as e:
        if conn:
            conn.close()
        return render_template('error.html', 
                             error_message=f"数据库查询错误: {str(e)}"), 500

# ========== API: 获取导入模板 ==========

@app.route('/admin/api/download_template')
@admin_required
def download_import_template():
    """下载导入模板CSV"""
    import io
    from flask import send_file
    
    # 创建模板数据
    template_data = {
        'Source_ID': [1],
        'Original_ID': ['EXAMPLE-001'],
        'Title_CN': ['示例文物'],
        'Title_EN': ['Example Artifact'],
        'Description_CN': ['这是一个示例描述'],
        'Classification': ['青铜器'],
        'Material': ['青铜'],
        'Date_CN': ['商代晚期'],
        'Date_EN': ['Late Shang Dynasty'],
        'Start_Year': [-1300],
        'End_Year': [-1046],
        'Geography': ['河南安阳'],
        'Culture': ['商文化'],
        'Artist': ['佚名'],
        'Credit_Line': ['某博物馆藏'],
        'Page_Link': ['https://example.com'],
        'Size_Type': ['高'],
        'Size_Value': [25.5],
        'Size_Unit': ['cm']
    }
    
    df = pd.DataFrame(template_data)
    
    # 创建内存中的CSV文件
    output = io.BytesIO()
    df.to_csv(output, index=False, encoding='utf-8-sig')
    output.seek(0)
    
    return send_file(
        output,
        mimetype='text/csv',
        as_attachment=True,
        download_name='artifact_import_template.csv'
    )                      

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(debug=True, host='0.0.0.0', port=port)