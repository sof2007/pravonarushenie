from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from flask_bootstrap import Bootstrap
from models import db, User, Offense
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta

app = Flask(__name__)
app.config.from_pyfile('config.py')
Bootstrap(app)
db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Предопределенные типы правонарушений
OFFENSE_TYPES = [
    'Произрастание на прилегающей территории сорной растительности высотой более 15 см',
    'Складирование на прилегающей территории строительных материалов, топлива, удобрения и иных движемых вещей',
    'Создание условий для подтопления соседних территорий и земельных участков',
    'кладирование металлического лома, строительного мусора, угля, дров и других материалов и отходов производства и потребления',
    'Хранение техники, механизмов, автомобилей (нагрузка на ось 3,5 т и более)'
]

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
@login_required
def dashboard():
    return render_template('dashboard.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash('Неверный логин или пароль')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/offenses')
@login_required
def offenses():
    offenses = Offense.query.all()
    return render_template('offenses.html', offenses=offenses)

from datetime import timedelta
from apscheduler.schedulers.background import BackgroundScheduler

# Инициализация планировщика
scheduler = BackgroundScheduler()
scheduler.start()

@app.route('/add_offense', methods=['GET', 'POST'])
@login_required
def add_offense():
    if request.method == 'POST':
        # Создаем объект правонарушения
        new_offense = Offense(
            address=request.form['address'],
            date=datetime.utcnow(),  # Используем текущую дату
            check_date=datetime.utcnow() + timedelta(days=7),  # Дата проверки через 7 дней
            offense_type=request.form['offense_type'],
            description=request.form.get('description', ''),
            user_id=current_user.id,
        )
        
        # Удалите строку offense.set_check_date() - она больше не нужна
        
        db.session.add(new_offense)
        db.session.commit()
        flash('Правонарушение добавлено')
        return redirect(url_for('offenses'))
    
    return render_template('add_offense.html', offense_types=OFFENSE_TYPES)

@app.route('/edit_offense/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_offense(id):
    offense = Offense.query.get_or_404(id)
    
    if request.method == 'POST':
        offense.address = request.form['address']
        offense.date = datetime.datetime.strptime(request.form['date'], '%Y-%m-%d')
        offense.offense_type = request.form['offense_type']
        offense.description = request.form.get('description', '')
        
        db.session.commit()
        flash('Правонарушение обновлено')
        return redirect(url_for('offenses'))
    
    return render_template('edit_offense.html', 
                         offense=offense, 
                         offense_types=OFFENSE_TYPES)

@app.route('/delete_offense/<int:id>', methods=['POST'])
@login_required
def delete_offense(id):
    offense = Offense.query.get_or_404(id)
    db.session.delete(offense)
    db.session.commit()
    flash('Правонарушение удалено')
    return redirect(url_for('offenses'))

@app.route('/users')
@login_required
def users():
    if not current_user.is_admin:
        flash('Доступ запрещен')
        return redirect(url_for('dashboard'))
    
    users = User.query.all()
    return render_template('users.html', users=users)

@app.route('/add_user', methods=['POST'])
@login_required
def add_user():
    if not current_user.is_admin:
        flash('Доступ запрещен')
        return redirect(url_for('dashboard'))
    
    username = request.form['username']
    password = generate_password_hash(request.form['password'])
    is_admin = 'is_admin' in request.form
    
    if User.query.filter_by(username=username).first():
        flash('Пользователь уже существует')
        return redirect(url_for('users'))
    
    new_user = User(
        username=username,
        password=password,
        is_admin=is_admin
    )
    
    db.session.add(new_user)
    db.session.commit()
    flash('Пользователь добавлен')
    return redirect(url_for('users'))

@app.route('/edit_user/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_user(id):
    if not current_user.is_admin:
        flash('Доступ запрещен')
        return redirect(url_for('dashboard'))
    
    user = User.query.get_or_404(id)
    
    if request.method == 'POST':
        user.username = request.form['username']
        if request.form['password']:
            user.password = generate_password_hash(request.form['password'])
        user.is_admin = 'is_admin' in request.form
        
        db.session.commit()
        flash('Пользователь обновлен')
        return redirect(url_for('users'))
    
    return render_template('edit_user.html', user=user)

@app.route('/delete_user/<int:id>', methods=['POST'])
@login_required
def delete_user(id):
    if not current_user.is_admin:
        flash('Доступ запрещен')
        return redirect(url_for('dashboard'))
    
    if current_user.id == id:
        flash('Нельзя удалить себя')
        return redirect(url_for('users'))
    
    user = User.query.get_or_404(id)
    db.session.delete(user)
    db.session.commit()
    flash('Пользователь удален')
    return redirect(url_for('users'))

@app.route('/reports', methods=['GET', 'POST'])  # ← Оба метода разрешены!
@login_required
def reports():
    if request.method == 'POST':
        # Обработка фильтров (даты, тип нарушения и т.д.)
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        offense_type = request.form.get('offense_type', 'Все')
        
        # Фильтрация данных
        query = Offense.query
        if start_date:
            query = query.filter(Offense.date >= start_date)
        if end_date:
            query = query.filter(Offense.date <= end_date)
        if offense_type != 'Все':
            query = query.filter_by(offense_type=offense_type)
        
        offenses = query.all()
        return render_template('reports.html', offenses=offenses)
    
    # GET-запрос: показать все нарушения
    offenses = Offense.query.all()
    return render_template('reports.html', offenses=offenses)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        if not User.query.filter_by(username='admin').first():
            admin = User(
                username='admin',
                password=generate_password_hash('admin'),
                is_admin=True
            )
            db.session.add(admin)
            db.session.commit()
    app.run(debug=True)
