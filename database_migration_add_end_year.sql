-- 数据库迁移脚本：为 ARTIFACTS 表添加 End_Year 字段
-- 执行日期：2025-12-15
-- 描述：添加文物的结束年代字段，用于更精确的年代范围表示

USE project;

-- 添加 End_Year 字段到 ARTIFACTS 表
ALTER TABLE ARTIFACTS 
ADD COLUMN End_Year INT DEFAULT NULL 
COMMENT '文物年代结束年份（负数表示公元前）'
AFTER Start_Year;

-- 验证字段是否添加成功
DESCRIBE ARTIFACTS;

-- 创建索引以优化年代范围查询
CREATE INDEX idx_year_range ON ARTIFACTS(Start_Year, End_Year);

-- 显示添加结果
SELECT 
    COLUMN_NAME, 
    DATA_TYPE, 
    IS_NULLABLE, 
    COLUMN_DEFAULT,
    COLUMN_COMMENT
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = 'project' 
  AND TABLE_NAME = 'ARTIFACTS' 
  AND COLUMN_NAME IN ('Start_Year', 'End_Year');

