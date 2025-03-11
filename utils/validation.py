import os
from dataclasses import dataclass
from pathlib import Path

from telethon import TelegramClient


@dataclass
class ValidationResult:
    is_valid: bool
    is_error: bool = False
    message: str = ''


class Validator:
    env_vars = ['API_ID', 'API_HASH', 'PHONE_NUMBER']

    @staticmethod
    def validate_env_file(env_filename: str = '.env') -> ValidationResult:
        if not Path(env_filename).is_file():
            log_msg = 'Отсутвует файл .env'
            return ValidationResult(is_valid=False, message=log_msg)
        return ValidationResult(is_valid=True)

    @staticmethod
    def validate_env_var(var_name: str, error_msg: str | None = None) -> ValidationResult:
        if os.getenv(var_name) is None:
            return ValidationResult(is_valid=False, message=error_msg)
        return ValidationResult(is_valid=True)

    @classmethod
    def validate_env_id(cls) -> ValidationResult:
        return cls.validate_env_var('API_ID', 'Отсутствует переменная API_ID')

    @classmethod
    def validate_env_hash(cls) -> ValidationResult:
        return cls.validate_env_var('API_HASH', 'Отсутствует переменная API_HASH')

    @classmethod
    def validate_env_phone_number(cls) -> ValidationResult:
        return cls.validate_env_var('PHONE_NUMBER', 'Отсутствует переменная PHONE_NUMBER')

    @classmethod
    def validate_env_vars(cls) -> ValidationResult:
        if all([cls.validate_env_var(var).is_valid for var in cls.env_vars]):
            return ValidationResult(is_valid=True)
        return ValidationResult(is_valid=False)

    @staticmethod
    async def validate_auth(client: TelegramClient) -> ValidationResult:
        try:
            if not client.is_connected():
                await client.connect()
            is_user_authorized = await client.is_user_authorized()
            if not is_user_authorized:
                log_msg = 'Клиент не авторизован'
                return ValidationResult(is_valid=False, message=log_msg)
            return ValidationResult(is_valid=True)
        except Exception as ex:
            log_msg = f'Ошибка при подключении клиента, код ошибки: {ex}'
            return ValidationResult(is_valid=False, is_error=True, message=log_msg)
        finally:
            if client.is_connected():
                await client.disconnect()