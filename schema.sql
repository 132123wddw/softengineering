-- 创建用户表
CREATE TABLE user (
    id INT PRIMARY KEY,  -- 用户的学号，唯一识别符
    name VARCHAR(255) NOT NULL,  -- 用户的姓名
    password VARCHAR(255) NOT NULL,  -- 用户密码的散列值
    major VARCHAR(255),  -- 专业
    google_scholar_link VARCHAR(255)  -- 谷歌学术链接
);

-- 创建师生关系表
CREATE TABLE teacher_student_relationship (
    student_id INT,  -- 关系中学生的id
    teacher_id INT,  -- 关系中老师的id
    PRIMARY KEY (student_id, teacher_id)  -- 组合主键，确保每对师生关系的唯一性
);
