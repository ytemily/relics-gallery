"""
SQL查询构建器
根据 db_config.py 中的配置自动生成SQL查询
"""

from db_config import QUERIES, TABLES, FIELDS, JOINS

def build_index_query():
    """构建首页查询SQL"""
    config = QUERIES['index']
    
    select_clause = ', '.join(config['select'])
    from_clause = f"{config['from']} {config['alias']}"
    
    # 构建JOIN子句
    join_clauses = []
    for join_config in config['joins']:
        join_clauses.append(
            f"LEFT JOIN {join_config['table']} {join_config['alias']} "
            f"ON {join_config['on']}"
        )
    
    query = f"""
        SELECT {select_clause}
        FROM {from_clause}
        {' '.join(join_clauses)}
        GROUP BY {config['group_by']}
        ORDER BY {config['order_by']}
    """
    
    return query.strip()

def build_detail_query():
    """构建详情页查询SQL"""
    config = QUERIES['detail']
    
    select_clause = ', '.join(config['select'])
    from_clause = f"{config['from']} {config['alias']}"
    
    # 构建JOIN子句
    join_clauses = []
    for join_config in config['joins']:
        join_clauses.append(
            f"LEFT JOIN {join_config['table']} {join_config['alias']} "
            f"ON {join_config['on']}"
        )
    
    query = f"""
        SELECT {select_clause}
        FROM {from_clause}
        {' '.join(join_clauses)}
        WHERE {config['where']}
    """
    
    return query.strip()

def build_images_query():
    """构建图片查询SQL"""
    config = QUERIES['images']
    
    select_clause = ', '.join(config['select'])
    from_clause = config['from']
    
    query = f"""
        SELECT {select_clause}
        FROM {from_clause}
        WHERE {config['where']}
        ORDER BY {config['order_by']}
    """
    
    return query.strip()

def build_search_query(search_term):
    """构建搜索查询SQL
    搜索范围包括：标题、艺术家、文化、来源、年代、描述、材质
    返回结果包含文化、材质和年代信息，用于筛选和排序
    """
    if not search_term:
        return None
    
    # 使用LIKE进行模糊匹配，支持中文搜索
    search_pattern = f"%{search_term}%"
    
    query = f"""
        SELECT DISTINCT 
            a.{FIELDS['artifact']['id']} AS artifact_id,
            a.{FIELDS['artifact']['title_cn']} AS title,
            a.{FIELDS['artifact']['date_cn']} AS date_text,
            ANY_VALUE(iv.{FIELDS['image']['local_path']}) AS local_path,
            ANY_VALUE(p.{FIELDS['property']['culture']}) AS culture_name,
            ANY_VALUE(a.{FIELDS['artifact']['material']}) AS medium,
            ANY_VALUE(a.{FIELDS['artifact']['start_year']}) AS start_year
        FROM {TABLES['artifacts']} a
        LEFT JOIN {TABLES['image_versions']} iv ON a.{FIELDS['artifact']['id']} = iv.{FIELDS['image']['artifact_id']}
        LEFT JOIN {TABLES['properties']} p ON a.{FIELDS['artifact']['id']} = p.{FIELDS['property']['artifact_id']}
        LEFT JOIN {TABLES['sources']} s ON a.{FIELDS['artifact']['source_id']} = s.{FIELDS['source']['id']}
        WHERE 
            a.{FIELDS['artifact']['title_cn']} LIKE %s
            OR a.{FIELDS['artifact']['title_en']} LIKE %s
            OR a.{FIELDS['artifact']['date_cn']} LIKE %s
            OR a.{FIELDS['artifact']['date_en']} LIKE %s
            OR a.{FIELDS['artifact']['material']} LIKE %s
            OR a.{FIELDS['artifact']['description_cn']} LIKE %s
            OR COALESCE(p.{FIELDS['property']['artist']}, '') LIKE %s
            OR COALESCE(p.{FIELDS['property']['culture']}, '') LIKE %s
            OR COALESCE(p.{FIELDS['property']['geography']}, '') LIKE %s
            OR COALESCE(s.{FIELDS['source']['museum_name_cn']}, '') LIKE %s
        GROUP BY a.{FIELDS['artifact']['id']}
        ORDER BY a.{FIELDS['artifact']['id']} DESC
    """
    
    return query.strip()

def build_cultures_browse_query():
    """构建文化浏览页面查询SQL
    返回所有文化及其文物数量和代表性图片（从PROPERTIES表获取文化信息）
    """
    query = f"""
        SELECT 
            p.{FIELDS['property']['culture']} AS culture_name,
            COUNT(DISTINCT a.{FIELDS['artifact']['id']}) AS artifact_count,
            ANY_VALUE(iv.{FIELDS['image']['local_path']}) AS representative_image
        FROM {TABLES['properties']} p
        LEFT JOIN {TABLES['artifacts']} a ON p.{FIELDS['property']['artifact_id']} = a.{FIELDS['artifact']['id']}
        LEFT JOIN {TABLES['image_versions']} iv ON a.{FIELDS['artifact']['id']} = iv.{FIELDS['image']['artifact_id']}
        WHERE p.{FIELDS['property']['culture']} IS NOT NULL AND p.{FIELDS['property']['culture']} != ''
        GROUP BY p.{FIELDS['property']['culture']}
        HAVING artifact_count > 0
        ORDER BY artifact_count DESC, p.{FIELDS['property']['culture']}
    """
    
    return query.strip()

def build_culture_artifacts_query(culture_name):
    """构建某个文化下的文物列表查询SQL（使用文化名称）"""
    query = f"""
        SELECT 
            a.{FIELDS['artifact']['id']} AS artifact_id,
            a.{FIELDS['artifact']['title_cn']} AS title,
            a.{FIELDS['artifact']['date_cn']} AS date_text,
            ANY_VALUE(iv.{FIELDS['image']['local_path']}) AS local_path
        FROM {TABLES['artifacts']} a
        LEFT JOIN {TABLES['properties']} p ON a.{FIELDS['artifact']['id']} = p.{FIELDS['property']['artifact_id']}
        LEFT JOIN {TABLES['image_versions']} iv ON a.{FIELDS['artifact']['id']} = iv.{FIELDS['image']['artifact_id']}
        WHERE p.{FIELDS['property']['culture']} = %s
        GROUP BY a.{FIELDS['artifact']['id']}
        ORDER BY a.{FIELDS['artifact']['id']} DESC
    """
    
    return query.strip()

# 使用示例（可选，如果使用配置化方案）
if __name__ == '__main__':
    print("首页查询：")
    print(build_index_query())
    print("\n详情页查询：")
    print(build_detail_query())
    print("\n图片查询：")
    print(build_images_query())
    print("\n搜索查询示例：")
    print(build_search_query("测试"))

