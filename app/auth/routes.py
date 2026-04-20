from flask import render_template, redirect, url_for, session, flash
from app.auth import bp
from app.extensions import db
from app.models.user import User
from app.auth.forms import RegisterForm, LoginForm

@bp.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        # Проверка существования пользователя
        existing_user = db.session.query(User).filter(User.email == form.email.data).first()
        if existing_user:
            flash('Пользователь с таким email уже существует', 'danger')
            return render_template('register.html', form=form)

        user = User(name=form.name.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()

        session['user_id'] = user.id
        session['user_name'] = user.name
        flash('Регистрация прошла успешно!', 'success')
        return redirect(url_for('index'))

    return render_template('register.html', form=form)

@bp.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = db.session.query(User).filter(User.email == form.email.data).first()
        if user and user.check_password(form.password.data):
            session['user_id'] = user.id
            session['user_name'] = user.name
            flash('Вы вошли в систему', 'success')
            return redirect(url_for('index'))
        flash('Неправильный email или пароль', 'danger')
    return render_template('login.html', form=form)

@bp.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('user_name', None)
    flash('Вы вышли из системы', 'info')
    return redirect(url_for('index'))