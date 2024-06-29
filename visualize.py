import sqlite3

# 连接到数据库
conn = sqlite3.connect('academic_tree.db')
cursor = conn.cursor()

# 查询用户表内容
print("User Table:")
cursor.execute("SELECT * FROM user;")
users = cursor.fetchall()
for user in users:
    print(user)

print("\n")

# 查询师生关系表内容
print("Teacher-Student Relationship Table:")
cursor.execute("SELECT * FROM teacher_student_relationship;")
relationships = cursor.fetchall()
for relationship in relationships:
    print(relationship)

print("\n")
# 关闭连接
conn.close()
