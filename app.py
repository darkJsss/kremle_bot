from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///war_history.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/images'

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

    results = db.relationship('TestResult', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class TestResult(db.Model):
    __tablename__ = 'test_results'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    test_name = db.Column(db.String(100), nullable=False)
    score = db.Column(db.Integer, nullable=False)
    max_score = db.Column(db.Integer, nullable=False)
    completed_at = db.Column(db.DateTime, default=datetime.utcnow)


def save_test_result(user_id, test_name, score, max_score):
    """
    Сохраняет или обновляет результат теста пользователя
    """
    result = TestResult.query.filter_by(
        user_id=user_id,
        test_name=test_name
    ).first()

    if result:
        # Обновляем существующий результат, если новый лучше
        if score > result.score:
            result.score = score
            result.max_score = max_score
            result.completed_at = datetime.utcnow()
    else:
        # Создаем новую запись
        result = TestResult(
            user_id=user_id,
            test_name=test_name,
            score=score,
            max_score=max_score
        )
        db.session.add(result)

    db.session.commit()
    return result


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


with app.app_context():
    db.create_all()


def load_tests():
    tests = {}
    test_files = {
        'Битва за Москву': 'tests/БитвазаМосквутест.txt',
        'Блокада Ленинграда': 'tests/БлокадаЛенинградатест.txt',
        'Курская битва': 'tests/Курскаябитватест.txt',
        'Сталинградская битва': 'tests/Сталинградскаябитватест.txt'
    }

    for name, filepath in test_files.items():
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read().split('\n\n')
                questions = []
                for block in content:
                    if block.strip():
                        lines = block.split('\n')
                        question = lines[0]
                        options = [opt for opt in lines[1:] if opt]
                        correct = [opt for opt in options if '✔️' in opt][0]
                        options = [opt.split(' ✔️')[0].strip() for opt in options]
                        questions.append({
                            'question': question,
                            'options': options,
                            'correct': correct.split(' ✔️')[0].strip()
                        })
                tests[name] = questions
        except FileNotFoundError:
            print(f"Файл теста не найден: {filepath}")
            tests[name] = []

    return tests


def load_theory():
    theory = {}
    theory_files = {
        'Битва за Москву': 'theory/БИТВАЗАМОСКВУ.txt',
        'Блокада Ленинграда': 'theory/ОБОРОНАЛЕНИНГРАДА.txt',
        'Курская битва': 'theory/КУРСКАЯБИТВА.txt',
        'Сталинградская битва': 'theory/СТАЛИНГРАДСКАЯБИТВА.txt'
    }

    for name, filepath in theory_files.items():
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                theory[name] = f.read()
        except FileNotFoundError:
            print(f"Файл теории не найден: {filepath}")
            theory[name] = "Материал временно недоступен"

    return theory


TESTS = load_tests()
THEORY = load_theory()


@app.route('/')
@login_required
def index():
    return render_template('index.html', username=current_user.username)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        if not username or not password:
            flash('Заполните все поля', 'error')
            return redirect(url_for('register'))

        if len(username) < 4 or len(username) > 20:
            flash('Имя пользователя должно быть от 4 до 20 символов', 'error')
            return redirect(url_for('register'))

        if password != confirm_password:
            flash('Пароли не совпадают', 'error')
            return redirect(url_for('register'))

        if len(password) < 6:
            flash('Пароль должен содержать не менее 6 символов', 'error')
            return redirect(url_for('register'))

        if User.query.filter_by(username=username).first():
            flash('Имя пользователя уже занято', 'error')
            return redirect(url_for('register'))

        user = User(username=username, is_active=True)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        flash('Регистрация успешна! Теперь вы можете войти', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = User.query.filter_by(username=username).first()

        if not user or not user.check_password(password):
            flash('Неверное имя пользователя или пароль', 'error')
            return redirect(url_for('login'))

        if not user.is_active:
            flash('Ваш аккаунт деактивирован', 'error')
            return redirect(url_for('login'))

        login_user(user)
        next_page = request.args.get('next')
        return redirect(next_page or url_for('index'))

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


@app.route('/theory')
@login_required
def theory():
    topics = [
        {'id': 1, 'title': 'Битва за Москву'},
        {'id': 2, 'title': 'Блокада Ленинграда'},
        {'id': 3, 'title': 'Курская битва'},
        {'id': 4, 'title': 'Сталинградская битва'}
    ]
    return render_template('theory.html', topics=topics)


@app.route('/theory/<int:topic_id>')
@login_required
def view_theory(topic_id):
    topic_map = {
        1: {'title': 'Битва за Москву', 'content': THEORY.get('Битва за Москву', '')},
        2: {'title': 'Блокада Ленинграда', 'content': THEORY.get('Блокада Ленинграда', '')},
        3: {'title': 'Курская битва', 'content': THEORY.get('Курская битва', '')},
        4: {'title': 'Сталинградская битва', 'content': THEORY.get('Сталинградская битва', '')}
    }

    topic = topic_map.get(topic_id)
    if not topic:
        flash('Тема не найдена', 'error')
        return redirect(url_for('theory'))

    return render_template('theory_detail.html', topic=topic)


@app.route('/tests')
@login_required
def tests():
    test_list = [
        {'id': 1, 'title': 'Битва за Москву', 'question_count': len(TESTS.get('Битва за Москву', []))},
        {'id': 2, 'title': 'Блокада Ленинграда', 'question_count': len(TESTS.get('Блокада Ленинграда', []))},
        {'id': 3, 'title': 'Курская битва', 'question_count': len(TESTS.get('Курская битва', []))},
        {'id': 4, 'title': 'Сталинградская битва', 'question_count': len(TESTS.get('Сталинградская битва', []))}
    ]
    return render_template('tests.html', tests=test_list)


@app.route('/test/<int:test_id>', methods=['GET', 'POST'])
@login_required
def take_test(test_id):
    test_map = {
        1: 'Битва за Москву',
        2: 'Блокада Ленинграда',
        3: 'Курская битва',
        4: 'Сталинградская битва'
    }

    test_name = test_map.get(test_id)
    if not test_name or test_name not in TESTS:
        flash('Тест не найден', 'error')
        return redirect(url_for('tests'))

    questions = TESTS[test_name]
    if not questions:
        flash('Вопросы для этого теста временно недоступны', 'error')
        return redirect(url_for('tests'))

    if request.method == 'POST':
        score = 0
        results = []

        for i, question in enumerate(questions):
            user_answer = request.form.get(f'question_{i}')
            is_correct = (user_answer == question['correct'])
            if is_correct:
                score += 1
            results.append({
                'question': question['question'],
                'user_answer': user_answer,
                'correct_answer': question['correct'],
                'is_correct': is_correct
            })

        # Используем функцию save_test_result
        save_test_result(
            user_id=current_user.id,
            test_name=test_name,
            score=score,
            max_score=len(questions)
        )

        return render_template('test_results.html', test_name=test_name, score=score, total=len(questions), results=results)

    return render_template('test.html', test_name=test_name, questions=questions, enumerate=enumerate)


@app.route('/profile')
@login_required
def profile():
    results = TestResult.query.filter_by(user_id=current_user.id).order_by(TestResult.completed_at.desc()).all()
    return render_template('profile.html', user=current_user, results=results)

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/leaderboard')
@login_required
def leaderboard():
    # Общий рейтинг (уже с enumerate в Python)
    overall_query = db.session.query(
        User.username,
        db.func.sum(TestResult.score).label('total_score')
    ).join(TestResult).group_by(User.id).order_by(db.desc('total_score')).all()

    # Подготавливаем данные с нумерацией
    overall = [(i + 1, username, score) for i, (username, score) in enumerate(overall_query)]

    # Рейтинг по тестам
    test_stats = {}
    for test_name in ['Битва за Москву', 'Блокада Ленинграда', 'Курская битва', 'Сталинградская битва']:
        stats_query = db.session.query(
            User.username,
            TestResult.score
        ).join(TestResult).filter(
            TestResult.test_name == test_name
        ).order_by(TestResult.score.desc()).limit(10).all()

        # Добавляем нумерацию
        test_stats[test_name] = [(i + 1, username, score) for i, (username, score) in enumerate(stats_query)]

    return render_template('leaderboard.html',
                           overall=overall,
                           test_stats=test_stats)

@app.route('/test_image')
def test_image():
    return f'''
    <h1>Проверка изображения</h1>
    <p>Путь: {url_for('static', filename='images/victory.png')}</p>
    <img src="{url_for('static', filename='images/victory.png')}" 
         style="width: 300px; border: 2px solid red">
    '''

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
