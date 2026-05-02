from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, FileRequired
from wtforms import StringField, PasswordField, SubmitField, EmailField
from wtforms.validators import DataRequired, EqualTo

class RegisterForm(FlaskForm):
    name = StringField('Имя', validators=[DataRequired()])
    email = EmailField('Email', validators=[DataRequired()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    password_again = PasswordField('Повторите пароль', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Зарегистрироваться')

class LoginForm(FlaskForm):
    email = EmailField('Email', validators=[DataRequired()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    submit = SubmitField('Войти')

class AvatarForm(FlaskForm):
    """Форма для загрузки аватара"""
    avatar = FileField('Выберите изображение',
                       validators=[
                           FileRequired(message='Файл обязателен'),
                           FileAllowed(['jpg', 'jpeg', 'png', 'gif', 'webp'],
                                     'Только изображения! (jpg, jpeg, png, gif, webp)')
                       ])
    submit = SubmitField('Загрузить')

class RemoveAvatarForm(FlaskForm):
    """Форма для удаления аватара"""
    submit = SubmitField('Удалить фото')