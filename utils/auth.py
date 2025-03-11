import asyncio
import os
import logging
from dataclasses import dataclass

from pathlib import Path

from telethon import TelegramClient, errors
from telethon.sessions import SQLiteSession, MemorySession
from telethon.sessions.abstract import Session

from utils.validation import Validator


@dataclass
class AuthState:
    session_type: str = 'sqlite'
    session_name: str = 'telegram_api_session'
    memory_session: MemorySession | None = None
    is_logging: bool = False

    is_auth: bool = False
    need_send_code: bool = False
    need_verify_code: bool = False
    need_verify_2fa: bool = False
    message: str | None = None
    client: TelegramClient | None = None

    def check_start_auth_status(self) -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self.check_is_auth())

    async def check_is_auth(self) -> None:
        if Validator.validate_env_vars().is_valid:
            client = ClientConnector.get_client(self.get_session(), os.getenv('API_ID'), os.getenv('API_HASH'))
            validation_result = await Validator.validate_auth(client)
            if validation_result.is_valid:
                self.set_auth_success()

    def get_session(self) -> Session:
        if self.session_type == 'sqlite':
            return SQLiteSession(self.session_name)
        elif self.session_type == 'memory':
            if self.memory_session is None:
                self.memory_session = MemorySession()
            return self.memory_session

    def change_session_type(self, session_type):
        if session_type != self.session_type:
            self.session_type = session_type

    def reset_state(self) -> None:
        defaults = self.__class__()
        # self.__dict__.update(defaults.__dict__)
        self.is_auth = defaults.is_auth
        self.need_send_code = defaults.need_send_code
        self.need_verify_code = defaults.need_verify_code
        self.need_verify_2fa = defaults.need_verify_2fa
        self.message = defaults.message
        self.client = defaults.client

    def _log(self) -> None:
        if self.is_logging and self.message:
            logging.info(self.message)

    def set_auth_failed(self, message: str | None = None) -> None:
        if message:
            self.message = message
        self._log()

    def set_start_auth(self) -> None:
        self.reset_state()
        self.message = 'Начата процедура аутентификации'

    def set_client(self, client: TelegramClient) -> None:
        self.client = client
        if self.session_type == 'memory':
            self.memory_session = client.session

    def set_need_send_code(self) -> None:
        self.need_send_code = True
        self.message = 'Проверка соединения клиента завершена успешно. Отправка проверочного кода'
        self._log()

    def set_need_verify_code(self) -> None:
        self.need_verify_code = True
        self.message = 'Код отправлен в Telegram. Введите его в поле Проверочный код'
        self._log()

    def set_need_verify_2fa(self) -> None:
        self.need_verify_2fa = True
        self.need_verify_code = False
        self.message = 'Требуется 2FA-пароль. Введите его в поле Облачный пароль'
        self._log()

    def set_auth_success(self, message: str | None = None) -> None:
        self.is_auth = True
        self.need_send_code = False
        self.need_verify_code = False
        self.need_verify_2fa = False
        self.message = 'Клиент авторизован' if message is None else message
        self._log()

    async def delete_session(self) -> None:
        if self.client is not None:
            await ClientConnector.log_out(self.client)
        if self.session_type == 'sqlite':
            session_filepath = Path(f'{self.session_name}.session')
            if session_filepath.is_file():
                session_filepath.unlink(missing_ok=True)
        elif self.session_type == 'memory':
            self.memory_session = None
        self.reset_state()
        self.message = 'Сессия удалена'
        self._log()


class ClientConnector:
    @staticmethod
    def get_client(session: Session, api_id: str, api_hash: str) -> TelegramClient:
        client = TelegramClient(session, api_id, api_hash, system_version='4.16.30-vxCUSTOM')
        return client
    
    @staticmethod
    async def connect(client: TelegramClient) -> None:
        if not client.is_connected():
            await client.connect()

    @staticmethod
    async def disconnect(client: TelegramClient) -> None:
        if client.is_connected():
            await client.disconnect()

    @classmethod
    async def log_out(cls, client: TelegramClient) -> None:
        await cls.connect(client)
        await client.log_out()
        await cls.disconnect(client)

    @classmethod
    async def start_auth(cls, state: AuthState, api_id: str, api_hash: str) -> AuthState:
        if not api_id or not api_hash:
            message = 'Не заданы api_id и/или api_hash'
            state.set_auth_failed(message=message)
            return state
        state.set_start_auth()
        client = cls.get_client(state.get_session(), api_id, api_hash)
        validation_result = await Validator.validate_auth(client)
        if validation_result.is_valid:
            message = 'Клиент авторизован'
            state.set_auth_success(message)
        elif not validation_result.is_valid and validation_result.is_error:
            state.set_auth_failed(message=validation_result.message)
        elif not validation_result.is_valid and not validation_result.is_error:
            state.set_client(client)
            state.set_need_send_code()
        return state

    @classmethod
    async def send_code(cls, state: AuthState, phone_number: str) -> AuthState:
        if not state.need_send_code:
            return state
        try:
            await cls.connect(state.client)
            await state.client.send_code_request(phone_number)
            state.set_need_verify_code()
        except Exception as ex:
            message = f'Ошибка при отправке кода подтверждения, код ошибки: {ex}'
            state.set_auth_failed(message)
        return state

    @classmethod
    async def verify_code(cls, state: AuthState, phone_number: str, code: str) -> AuthState:
        if not state.need_verify_code:
            return state
        try:
            await state.client.sign_in(phone=phone_number, code=code)
            await cls.disconnect(state.client)
            state.set_auth_success()
        except errors.SessionPasswordNeededError:
            state.set_need_verify_2fa()
        except Exception as ex:
            message = f'Ошибка при верификации кода подтверждения, код ошибки: {ex}'
            state.set_auth_failed(message)
        return state

    @classmethod
    async def verify_2fa(cls, state: AuthState, password_2fa: str) -> AuthState:
        if not state.need_verify_2fa:
            return state
        try:
            await state.client.sign_in(password=password_2fa)
            state.set_auth_success()
            await cls.disconnect(state.client)
        except Exception as ex:
            message = f'Ошибка при верификации облачного пароля, код ошибки: {ex}'
            state.set_auth_failed(message)
        return state

    @staticmethod
    def delete_all_session_files(path: str = '.') -> None:
        session_files = list(Path(path).glob('*.session'))
        for session_file in session_files:
            session_file.unlink(missing_ok=True)

