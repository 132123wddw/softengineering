from flask import Flask, render_template, request, redirect, url_for, g, session, flash
from werkzeug.security import generate_password_hash, check_password_hash

import sqlite3
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # 用于会话管理

# 配置数据库文件路径
DATABASE = 'academic_tree.db'

# 获取数据库连接
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
    return db

# 初始化数据库
def init_db():
    with app.app_context():
        db = get_db()
        # 使用内置的 open 函数读取 schema.sql 文件，指定 utf-8 编码
        with open('schema.sql', mode='r', encoding='utf-8') as f:
            db.cursor().executescript(f.read())
        db.commit()
        # print("Database initialized with schema.sql")

# 查询数据库并返回结果
def query_db(query, args=(), one=False):
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    # print(query, args, rv)
    return (rv[0] if rv else None) if one else rv

# 更新数据库
def execute_db(query, args=()):
    db = get_db()
    cur = db.execute(query, args)
    db.commit()
    return cur.lastrowid

# 增加用户
def add_user(id, name, password, major, google_scholar_link):
    hashed_password = generate_password_hash(password)
    try:
        execute_db(
            'INSERT INTO user (id, name, password, major, google_scholar_link) VALUES (?, ?, ?, ?, ?)',
            (id, name, hashed_password, major, google_scholar_link)
        )
        flash('User registered successfully.')
    except sqlite3.IntegrityError:
        flash('User ID already exists.')

# 删除用户
def delete_user(id):
    # 删除用户前，首先要删除与该用户相关的所有师生关系
    execute_db('DELETE FROM teacher_student_relationship WHERE student_id = ? OR teacher_id = ?', (id, id))
    execute_db('DELETE FROM user WHERE id = ?', (id,))
    flash('User deleted successfully.')

# 增加师生关系
def add_relationship(student_id, teacher_id):
    try:
        execute_db(
            'INSERT INTO teacher_student_relationship (student_id, teacher_id) VALUES (?, ?)',
            (student_id, teacher_id)
        )
        flash('Relationship added successfully.')
    except sqlite3.IntegrityError:
        flash('Relationship already exists or invalid IDs.')

# 删除师生关系
def delete_relationship(student_id, teacher_id):
    execute_db(
        'DELETE FROM teacher_student_relationship WHERE student_id = ? AND teacher_id = ?',
        (student_id, teacher_id)
    )
    flash('Relationship deleted successfully.')

# 获取用户信息
def get_user_by_id(id):
    user = query_db('SELECT * FROM user WHERE id = ?', (id,), one=True)
    if user:
        return {
            'id': user[0],
            'name': user[1],
            'password': user[2],
            'major': user[3],
            'google_scholar_link': user[4]
        }
    return None

# def get_user_by_id(id):
#     return query_db('SELECT * FROM user WHERE id = ?', (id,), one=True)

# 获取一个人的学生
def get_students(teacher_id):
    students = query_db(
        'SELECT user.id, user.name, user.major, user.google_scholar_link '
        'FROM user JOIN teacher_student_relationship ON user.id = teacher_student_relationship.student_id '
        'WHERE teacher_student_relationship.teacher_id = ?',
        (teacher_id,)
    )
    return [{'id': student[0], 'name': student[1], 'major': student[2], 'google_scholar_link': student[3]} for student in students]

# 获取一个人的老师
def get_teachers(student_id):
    teachers = query_db(
        'SELECT user.id, user.name, user.major, user.google_scholar_link '
        'FROM user JOIN teacher_student_relationship ON user.id = teacher_student_relationship.teacher_id '
        'WHERE teacher_student_relationship.student_id = ?',
        (student_id,)
    )
    return [{'id': teacher[0], 'name': teacher[1], 'major': teacher[2], 'google_scholar_link': teacher[3]} for teacher in teachers]

# 清理数据库连接
@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def verify_password(user_id, password):
    user = get_user_by_id(user_id)
    if user:
        return check_password_hash(user['password'], password)
    return False

def update_password(user_id, new_password):
    hashed_password = generate_password_hash(new_password)
    execute_db('UPDATE user SET password = ? WHERE id = ?', (hashed_password, user_id))

def update_user_info(user_id, new_name, new_major, new_google_scholar_link):
    execute_db(
        'UPDATE user SET name = ?, major = ?, google_scholar_link = ? WHERE id = ?',
        (new_name, new_major, new_google_scholar_link, user_id)
    )


# 用户注册路由
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        id = request.form['id']
        name = request.form['name']
        password = request.form['password']
        major = request.form.get('major')
        google_scholar_link = request.form.get('google_scholar_link')

        if not id or not name or not password:
            flash('Student ID, Name and Password are required!')
            return redirect(url_for('register'))
        
        if get_user_by_id(id):
            flash('User ID already exists.')
            return redirect(url_for('register'))

        add_user(id, name, password, major, google_scholar_link)
        return redirect(url_for('login'))
    return render_template('register.html')

# 用户登录路由
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        id = request.form['id']
        password = request.form['password']

        user = get_user_by_id(id)
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['user_name'] = user['name']
            flash('Logged in successfully.')
            return redirect(url_for('index'))
        else:
            flash('Invalid ID or password.')
            return redirect(url_for('login'))
    return render_template('login.html')

# 用户注销路由
@app.route('/logout')
def logout():
    session.clear()
    flash('You were successfully logged out')
    return redirect(url_for('index'))

# 主页路由
@app.route('/')
def index():
    # if 'user_id' in session:
    #     return f'Logged in as {session["user_name"]} (ID: {session["user_id"]})'
    # return 'You are not logged in'
    user_query = query_db('SELECT user.id, user.name, user.major, user.google_scholar_link FROM user')
    all_users=[{'id': user[0], 'name': user[1], 'major': user[2], 'google_scholar_link': user[3]} for user in user_query]

    return render_template('index.html', all_users=all_users)

# 编辑个人信息及修改密码路由
@app.route('/edit_profile', methods=['GET', 'POST'])
def edit_profile():
    if 'user_id' not in session:
        flash('Please log in first', 'error')
        return redirect(url_for('login'))

    user_id = session['user_id']

    if request.method == 'POST':
        if request.form.get('name'):
            # 处理个人信息的表单提交
            new_name = request.form['name']
            new_major = request.form['major']
            new_google_scholar_link = request.form['google_scholar_link']
            
            # 更新个人信息
            update_user_info(user_id, new_name, new_major, new_google_scholar_link)
            flash('Your profile has been updated successfully.', 'success')
        
        elif request.form.get('current_password'):
            # 处理密码修改的表单提交
            current_password = request.form['current_password']
            new_password = request.form['new_password']
            confirm_new_password = request.form['confirm_new_password']

            # 检查新密码和确认密码是否匹配
            if new_password != confirm_new_password:
                flash('New password and confirm password must match.', 'error')
            elif not verify_password(user_id, current_password):
                flash('Incorrect current password.', 'error')
            else:
                update_password(user_id, new_password)
                flash('Password updated successfully.', 'success')

    # 获取当前用户信息、老师和学生
    user = get_user_by_id(user_id)
    teachers = get_teachers(user_id)
    students = get_students(user_id)

    if user:
        return render_template('edit_profile.html', user=user, teachers=teachers, students=students)
    else:
        flash('User not found', 'error')
        return redirect(url_for('index'))


# 修改密码路由
@app.route('/change_password', methods=['POST'])
def change_password():
    if 'user_id' not in session:
        flash('Please log in first', 'error')
        return redirect(url_for('login'))

    user_id = session['user_id']
    current_password = request.form['current_password']
    new_password = request.form['new_password']
    confirm_new_password = request.form['confirm_new_password']

    # 检查新密码和确认密码是否匹配
    if new_password != confirm_new_password:
        flash('New password and confirm password must match', 'error')
        return redirect(url_for('edit_profile'))

    # 假设有验证当前密码的函数 verify_password(user_id, current_password) 和更新密码的函数 update_password(user_id, new_password)
    if not verify_password(user_id, current_password):
        flash('Incorrect current password', 'error')
        return redirect(url_for('edit_profile'))

    # 更新密码
    update_password(user_id, new_password)
    flash('Password updated successfully', 'success')
    return redirect(url_for('edit_profile'))

# 编辑老师路由
@app.route('/edit_teachers', methods=['GET', 'POST'])
def edit_teachers():
    if 'user_id' not in session:
        flash('Please log in first', 'error')
        return redirect(url_for('login'))

    user_id = session['user_id']
    teachers = get_teachers(user_id)
    user_query = query_db('SELECT user.id, user.name, user.major, user.google_scholar_link FROM user WHERE user.id != ?', (user_id,))
    all_users=[{'id': user[0], 'name': user[1], 'major': user[2], 'google_scholar_link': user[3]} for user in user_query]
    # print(all_users)
    return render_template('edit_teachers.html', teachers=teachers, all_users=all_users)

# 添加老师路由
@app.route('/add_teacher', methods=['POST'])
def add_teacher():
    if 'user_id' not in session:
        flash('Please log in first', 'error')
        return redirect(url_for('login'))
    
    student_id = session['user_id']
    teacher_id = request.form['teacher_id']

    if student_id == teacher_id:
        flash('You cannot add yourself as your own teacher', 'error')
        return redirect(url_for('edit_teachers'))

    add_relationship(student_id, teacher_id)
    return redirect(url_for('edit_teachers'))

# 删除老师路由
@app.route('/delete_teacher/<int:teacher_id>', methods=['POST'])
def delete_teacher(teacher_id):
    student_id = session['user_id']
    try:
        execute_db(
            'DELETE FROM teacher_student_relationship WHERE student_id = ? AND teacher_id = ?',
            (student_id, teacher_id)
        )
        flash('Teacher deleted successfully.', 'success')
    except Exception as e:
        flash('Error deleting teacher.', 'error')
        # print(e)  # Log the exception for debugging purposes

    return redirect(url_for('edit_teachers'))

# 编辑学生路由
@app.route('/edit_students', methods=['GET', 'POST'])
def edit_students():
    if 'user_id' not in session:
        flash('Please log in first', 'error')
        return redirect(url_for('login'))

    user_id = session['user_id']
    students = get_students(user_id)
    user_query = query_db('SELECT user.id, user.name, user.major, user.google_scholar_link FROM user WHERE user.id != ?', (user_id,))
    all_users=[{'id': user[0], 'name': user[1], 'major': user[2], 'google_scholar_link': user[3]} for user in user_query]
    # print(all_users)
    return render_template('edit_students.html', students=students, all_users=all_users)

# 删除学生路由
@app.route('/delete_student/<int:student_id>', methods=['POST'])
def delete_student(student_id):
    teacher_id = session['user_id']
    try:
        execute_db(
            'DELETE FROM teacher_student_relationship WHERE student_id = ? AND teacher_id = ?',
            (student_id, teacher_id)
        )
        flash('Student deleted successfully.', 'success')
    except Exception as e:
        flash('Error deleting student.', 'error')
        # print(e)  # Log the exception for debugging purposes

    return redirect(url_for('edit_students'))

# 添加学生路由
@app.route('/add_student', methods=['POST'])
def add_student():
    if 'user_id' not in session:
        flash('Please log in first', 'error')
        return redirect(url_for('login'))
    
    student_id = request.form['student_id']
    teacher_id = session['user_id']

    if teacher_id == student_id:
        flash('You cannot add yourself as your own student', 'error')
        return redirect(url_for('edit_students'))

    add_relationship(student_id, teacher_id)
    return redirect(url_for('edit_students'))

# 显示用户详细信息路由
@app.route('/user_info/<int:user_id>')
def user_info(user_id):
    user_query = query_db('SELECT * FROM user WHERE id = ?', (user_id,), one=True)
    if user_query is None:
        flash('User not found.', 'error')
        return redirect(url_for('index'))
    user={'id': user_query[0], 'name': user_query[1], 'major': user_query[3], 'google_scholar_link': user_query[4]}
    # print(user)

    teachers = get_teachers(user_id)
    students = get_students(user_id)

    fellowsProc = set()
    for teacher in teachers:
        stuArr = get_students(teacher['id'])
        for stu in stuArr:
            if stu['id']!=user['id']:
                fellowsProc.add(stu['id'])
    
    # print(fellowsProc)

    fellows=[]
    for id in fellowsProc:
        fellows.append(get_user_by_id(id))

    # print(fellows)

    return render_template('info.html', user=user, teachers=teachers, students=students, fellows=fellows)


@app.route('/search', methods=['GET'])
def search_results():
    search_query = request.args.get('q', '')
    user_query = query_db('SELECT user.id, user.name, user.major, user.google_scholar_link FROM user')
    all_users = [{'id': user[0], 'name': user[1], 'major': user[2], 'google_scholar_link': user[3]} for user in user_query]
    if search_query:
        search_results = [user for user in all_users if search_query.lower() in user['name'].lower()]
    else:
        search_results = []

    return render_template('search.html', search_query=search_query, search_results=search_results)


# 初始化数据库并运行服务器
if __name__ == '__main__':
    try:
        init_db()  # 初始化数据库（仅在首次运行时执行）
    except:
        pass
    app.run(debug=True)
