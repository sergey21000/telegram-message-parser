import os
from pathlib import Path
from typing import Callable, Collection

import gradio as gr
from telethon.sessions import SQLiteSession, MemorySession

from utils.auth import AuthState
from utils.parser import Parser
from utils.validation import Validator


class Components:

    welcome_message_markdown = '''
<h5 style='text-align: center'>
    Парсер сообщений Telegram
</h5>
<h6 style='text-align: center'>
    <a 
        href="https://github.com/sergey21000/telegram-message-parser" 
        target='_blank'>GitHub
    </a>
    проекта с инструкциями по получению `API_ID` и `API_HASH` приложения Telegram
</h6>
    '''

    @staticmethod
    def _create_env_var_textbox(
            env_var: str | None = None,
            validator_method: Callable | None = None,
            **kwargs,
            ) -> gr.Textbox:
        value = None
        if env_var and validator_method:
            validation_result = validator_method()
            if validation_result.is_valid:
                value = os.getenv(env_var)
        curr_kwargs = dict(value=value)
        curr_kwargs.update(kwargs)
        return gr.Textbox(**curr_kwargs)

    @classmethod
    def api_id(cls) -> gr.Textbox:
        return cls._create_env_var_textbox(
            env_var='API_ID',
            validator_method=Validator.validate_env_id,
            label='API_ID Telegram app',
            placeholder='API_ID приложения Telegram',
            scale=1,
            )

    @classmethod
    def api_hash(cls) -> gr.Textbox:
        return cls._create_env_var_textbox(
            env_var='API_HASH',
            validator_method=Validator.validate_env_hash,
            label='API_HASH Telegram app',
            placeholder='API_HASH приложения Telegram',
            scale=1,
            )

    @classmethod
    def phone_number(cls) -> gr.Textbox:
        return cls._create_env_var_textbox(
            env_var='PHONE_NUMBER',
            validator_method=Validator.validate_env_phone_number,
            label='PHONE_NUMBER Telegram app',
            placeholder='PHONE_NUMBER приложения Telegram',
            scale=1,
            )

    @staticmethod
    def code(visible: str = False, render: bool = True) -> gr.Textbox:
        component = gr.Textbox(
            value=None,
            label='Проверочный код',
            visible=visible,
            render=render,
            placeholder=None,
            scale=1,
            )
        return component

    @staticmethod
    def password_2fa(visible: str = False, render: bool = True) -> gr.Textbox:
        component = gr.Textbox(
            type='password',
            value=None,
            label='Облачный пароль',
            visible=visible,
            render=render,
            placeholder=None,
            scale=1,
            )
        return component

    @staticmethod
    def auth_status(value: str | None = None) -> gr.Textbox:
        component = gr.Textbox(
            value=value,
            label='Статус авторизации',
            placeholder=None,
            interactive=False,
            scale=1,
            )
        return component

    @staticmethod
    def auth_btn(interactive: bool = True) -> gr.Button:
        component = gr.Button(
            value='Авторизация',
            interactive=interactive,
            scale=1,
            )
        return component

    @staticmethod
    def code_btn(visible: bool = False, render: bool = True) -> gr.Button:
        component = gr.Button(
            value='Подтвержение кода',
            visible=visible,
            render=render,
            scale=0,
            )
        return component

    @staticmethod
    def password_2fa_btn(visible: bool = False, render: bool = True) -> gr.Button:
        component = gr.Button(
            value='Подтверждение облачного пароля',
            visible=visible,
            render=render,
            scale=0,
            )
        return component

    @staticmethod
    def delete_session_btn(visible: bool = False, render: bool = True) -> gr.Button:
        component = gr.Button(
            value='Удаление сессии',
            visible=visible,
            render=render,
            scale=1,
            )
        return component

    @classmethod
    def session_type_radio(cls) -> gr.Radio:
        session_types = {'sqlite': SQLiteSession, 'memory': MemorySession}
        component = gr.Radio(
            choices=session_types,
            value='sqlite',
            label='Тип сессии',
            info=None,  # cls.session_type_markdown
            )
        return component

    @staticmethod
    def chats_usernames() -> gr.Textbox:
        component = gr.Textbox(
            label='Адреса чатов',
            placeholder='Ссылки или ID чатов/каналов через пробел или перенос строки',
            scale=1,
            lines=2,
            )
        return component

    @staticmethod
    def add_chat_btn() -> gr.Button:
        component = gr.Button(
            value='Добавить чат/чаты',
            scale=0,
            )
        return component

    @staticmethod
    def chats_list_status() -> gr.Textbox:
        component = gr.Textbox(
            label='Добавленные чаты',
            placeholder='Здесь будет список чатов для парсинга',
            scale=1,
            lines=3,
            )
        return component

    @staticmethod
    def parse_status() -> gr.Textbox:
        component = gr.Textbox(
            label='Статус парсинга',
            placeholder='Здесь будет отчет о результатах парсинга',
            scale=1,
            lines=8,
            )
        return component

    @staticmethod
    def start_parse_btn() -> gr.Button:
        component = gr.Button(
            value='Начать парсинг',
            scale=0,
            )
        return component

    @staticmethod
    def download_btn(value: str | None = None) -> gr.Button:
        component = gr.DownloadButton(
            label='Загрузить csv результаты',
            value=value,
            visible=value is not None,
            scale=0,
            )
        return component

    @staticmethod
    def get_parse_args() -> list[gr.component]:
        limit = gr.Number(
            value=None,
            label='limit',
            info='Сколько сообщений парсить',
            )
        offset_date = gr.DateTime(
            value=None,
            label='offset_date',
            info='До какой даты парсить',
            timezone='Europe/Moscow',
            )
        reverse = gr.Checkbox(
            value=False,
            label='reverse',
            info='Парсить от сегодняшнего сообщения к самому раннему',
        )
        parse_args = [limit, offset_date, reverse]
        return parse_args


class ComponentsFn(Components):
    @staticmethod
    def update_status(auth_state: AuthState) -> str | None:
        return auth_state.message

    @classmethod
    def get_dynamic_visible_components(cls, auth_state: AuthState, render: bool = True) -> tuple[gr.component]:
        code = cls.code(visible=auth_state.need_verify_code, render=render)
        code_btn = cls.code_btn(visible=auth_state.need_verify_code, render=render)

        password_2fa = cls.password_2fa(visible=auth_state.need_verify_2fa, render=render)
        password_2fa_btn = cls.password_2fa_btn(visible=auth_state.need_verify_2fa, render=render)

        delete_session_btn = cls.delete_session_btn(visible=auth_state.is_auth, render=render)
        return code, code_btn, password_2fa, password_2fa_btn, delete_session_btn

    @staticmethod
    def update_auth_state_session_type(auth_state: AuthState, session_type: str) -> None:
        auth_state.change_session_type(session_type)

    @staticmethod
    async def delete_session(auth_state: AuthState) -> None:
        await auth_state.delete_session()

    @classmethod
    def update_download_btn(cls, csv_paths: Collection[Path]) -> gr.Button | None:
        if len(csv_paths) == 0:
            return None
        elif len(csv_paths) == 1:
            filepath = csv_paths[0]
        else:
            filepath = Parser.zip_files(csv_paths)
        component = cls.download_btn(value=filepath)
        return component
