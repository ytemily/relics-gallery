"""
数据库结构配置文件
根据 project_database.sql 中的新结构配置
数据库名称: project
"""

# 表名配置（新结构）
TABLES = {
    'sources': 'SOURCES',
    'artifacts': 'ARTIFACTS',
    'dimensions': 'DIMENSIONS',
    'properties': 'PROPERTIES',
    'image_versions': 'IMAGE_VERSIONS',
    'logs': 'LOGS'
}

# 字段名配置（新结构）
FIELDS = {
    # SOURCES 表字段
    'source': {
        'id': 'Source_ID',
        'museum_code': 'Museum_Code',
        'museum_name_cn': 'Museum_Name_CN'
    },
    # ARTIFACTS 表字段
    'artifact': {
        'id': 'Artifact_PK',
        'source_id': 'Source_ID',
        'original_id': 'Original_ID',
        'title_cn': 'Title_CN',
        'title_en': 'Title_EN',
        'description_cn': 'Description_CN',
        'classification': 'Classification',
        'material': 'Material',
        'date_cn': 'Date_CN',
        'date_en': 'Date_EN',
        'start_year': 'Start_Year',
        'end_year': 'End_Year'
    },
    # DIMENSIONS 表字段
    'dimension': {
        'id': 'Dimension_PK',
        'artifact_id': 'Artifact_PK',
        'size_type': 'Size_Type',
        'size_value': 'Size_Value',
        'size_unit': 'Size_Unit'
    },
    # PROPERTIES 表字段
    'property': {
        'id': 'Property_PK',
        'artifact_id': 'Artifact_PK',
        'geography': 'Geography',
        'culture': 'Culture',
        'artist': 'Artist',
        'credit_line': 'Credit_Line',
        'page_link': 'Page_Link'
    },
    # IMAGE_VERSIONS 表字段
    'image': {
        'id': 'Version_PK',
        'artifact_id': 'Artifact_PK',
        'version_type': 'Version_Type',
        'image_link': 'Image_Link',
        'local_path': 'Local_Path',
        'file_size_kb': 'File_Size_KB',
        'processed_format': 'Processed_Format',
        'processed_resolution': 'Processed_Resolution',
        'compression_ratio': 'Compression_Ratio',
        'last_processed_time': 'Last_Processed_Time'
    }
}

# 关联关系配置
JOINS = {
    'sources': {
        'table': TABLES['sources'],
        'on': f"a.{FIELDS['artifact']['source_id']} = s.{FIELDS['source']['id']}",
        'alias': 's',
        'select': f"s.{FIELDS['source']['museum_name_cn']} AS museum_name"
    },
    'properties': {
        'table': TABLES['properties'],
        'on': f"a.{FIELDS['artifact']['id']} = p.{FIELDS['property']['artifact_id']}",
        'alias': 'p',
        'select': [
            f"p.{FIELDS['property']['geography']} AS geography",
            f"p.{FIELDS['property']['culture']} AS culture_name",
            f"p.{FIELDS['property']['artist']} AS artist_name",
            f"p.{FIELDS['property']['credit_line']} AS credit_text",
            f"p.{FIELDS['property']['page_link']} AS source_url"
        ]
    },
    'image_versions': {
        'table': TABLES['image_versions'],
        'on': f"a.{FIELDS['artifact']['id']} = iv.{FIELDS['image']['artifact_id']}",
        'alias': 'iv',
        'select': f"ANY_VALUE(iv.{FIELDS['image']['local_path']}) as local_path"
    }
}

# 查询配置（保持向后兼容的字段别名）
QUERIES = {
    'index': {
        'select': [
            f"a.{FIELDS['artifact']['id']} AS artifact_id",
            f"a.{FIELDS['artifact']['title_cn']} AS title",
            f"a.{FIELDS['artifact']['date_cn']} AS date_text",
            JOINS['image_versions']['select']
        ],
        'from': TABLES['artifacts'],
        'alias': 'a',
        'joins': [JOINS['image_versions']],
        'group_by': f"a.{FIELDS['artifact']['id']}",
        'order_by': f"a.{FIELDS['artifact']['id']} DESC"
    },
    'detail': {
        'select': [
            f"a.{FIELDS['artifact']['id']} AS artifact_id",
            f"a.{FIELDS['artifact']['title_cn']} AS title",
            f"a.{FIELDS['artifact']['title_en']} AS title_en",
            f"a.{FIELDS['artifact']['description_cn']} AS description",
            f"a.{FIELDS['artifact']['classification']} AS classification",
            f"a.{FIELDS['artifact']['material']} AS medium",
            f"a.{FIELDS['artifact']['date_cn']} AS date_text",
            f"a.{FIELDS['artifact']['date_en']} AS date_en",
            f"a.{FIELDS['artifact']['original_id']} AS original_id",
            # 属性信息
            f"p.{FIELDS['property']['geography']} AS geography",
            f"p.{FIELDS['property']['culture']} AS culture_name",
            f"p.{FIELDS['property']['artist']} AS artist_name",
            f"p.{FIELDS['property']['credit_line']} AS credit_text",
            f"p.{FIELDS['property']['page_link']} AS source_url",
            # 来源信息
            f"s.{FIELDS['source']['museum_name_cn']} AS dept_name"
        ],
        'from': TABLES['artifacts'],
        'alias': 'a',
        'joins': [
            {'table': TABLES['properties'], 'alias': 'p', 'on': f"a.{FIELDS['artifact']['id']} = p.{FIELDS['property']['artifact_id']}"},
            {'table': TABLES['sources'], 'alias': 's', 'on': f"a.{FIELDS['artifact']['source_id']} = s.{FIELDS['source']['id']}"}
        ],
        'where': f"a.{FIELDS['artifact']['id']} = %s"
    },
    'images': {
        'select': [f"iv.{FIELDS['image']['local_path']} AS local_path"],
        'from': TABLES['image_versions'],
        'alias': 'iv',
        'where': f"iv.{FIELDS['image']['artifact_id']} = %s",
        'order_by': f"iv.{FIELDS['image']['id']}"
    },
    'dimensions': {
        'select': [
            f"d.{FIELDS['dimension']['size_type']} AS size_type",
            f"d.{FIELDS['dimension']['size_value']} AS size_value",
            f"d.{FIELDS['dimension']['size_unit']} AS size_unit"
        ],
        'from': TABLES['dimensions'],
        'alias': 'd',
        'where': f"d.{FIELDS['dimension']['artifact_id']} = %s"
    }
}
