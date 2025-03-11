import asyncio
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Collection

import pandas as pd
import gradio as gr
from telethon import TelegramClient, types, errors

from utils.auth import AuthState, ClientConnector
from utils.validation import Validator


MESSAGE_DICT = dict[str, str | int | datetime | None]
DEFAULT_PARSE_KWARGS = dict(
    limit=None,
    offset_date=None,
    reverse=False,
)


@dataclass
class Chat:
    chat: types.TLObject
    chat_name: str | None
    chat_username: str
    chat_type: str
    chat_id: int

    @classmethod
    def from_telethon_chat(cls, chat: types.TLObject, chat_username: str):
        chat_id = chat.id
        if isinstance(chat, types.User):
            chat_type = 'Chat'
            chat_name = f'{chat.first_name} {chat.last_name}'
        else:
            chat_type = 'Channel/Group'
            chat_name = chat.title
        return cls(chat, chat_name, chat_username, chat_type, chat_id)

    def get_chat_info(self) -> str:
        chat_info = f'Chat name: {self.chat_name}, Chat type: {self.chat_type}, Chat ID: {self.chat_id}'
        return chat_info


class Parser:
    parse_results_dir = Path('parse_results_dir')

    @staticmethod
    def message_to_dict(message: types.Message) -> MESSAGE_DICT:
        text = message.text if message.text else message.message
        if not text:
            return None

        date = message.date
        sender = message.sender
        sender_type = type(sender).__name__
        chat = message._chat
        chat_id = chat.id
        chat_type = type(chat).__name__
        chat_name = chat.title if isinstance(chat, types.Channel) else f'{chat.first_name} {chat.last_name}'

        if isinstance(sender, types.User):
            sender_id = message.sender.id
            username = sender.username
            first_name = sender.first_name
            last_name = sender.last_name
        else:
            sender_id = message._sender_id
            username = getattr(message.sender, 'username', None)
            first_name = None
            last_name = None

        message_dict = {
            'date': date,
            'chat_type': chat_type,
            'chat_name': chat_name,
            'chat_id': chat_id,
            'sender_type': sender_type,
            'sender_username': username,
            'sender_first_name': first_name,
            'sender_last_name': last_name,
            'sender_id': sender_id,
            'text': text,
        }
        return message_dict

    @classmethod
    async def get_messages_from_chat(
        cls,
        client: TelegramClient,
        chat: types.TLObject,
        parse_chats_pb_info: str,
        **parse_kwargs,
        ) -> list[MESSAGE_DICT]:

        async with client:
            progress = gr.Progress()
            messages = client.iter_messages(entity=chat, **parse_kwargs)
            message_dicts = []
            message_count = 0
            async for message in messages:
                message_count += 1
                if message_count % 1000 == 0:
                    await asyncio.sleep(1)
                message_dict = cls.message_to_dict(message)
                if message_dict is not None:
                    message_dicts.append(message_dict)

                if message_count % 1000 == 0:
                    await asyncio.sleep(1)

                if parse_kwargs['limit'] is not None:
                    total = parse_kwargs['limit']
                    progress(message_count / total, desc=f'{parse_chats_pb_info}, Parsing messages {message_count}/{total}')
                else:
                    progress(message_count, desc=f'{parse_chats_pb_info}, Parsing messages {message_count}/?')

        if not parse_kwargs['reverse']:
            message_dicts = message_dicts[::-1]
        return message_dicts

    @classmethod
    async def parse_chats(
        cls, 
        auth_state: AuthState,
        chats_list: list[Chat],
        api_id: str,
        api_hash: str,
        *parse_args,
        ) -> tuple[str, list[Path]]:

        cvs_paths = []
        parse_result = ''

        if len(chats_list) == 0:
            return 'Список чатов для парсинга пустой', cvs_paths

        client = ClientConnector.get_client(auth_state.get_session(), api_id, api_hash)
        validation_result = await Validator.validate_auth(client)
        if not validation_result.is_valid:
            return 'Клиент не авторизован', cvs_paths

        parse_kwargs = dict(zip(DEFAULT_PARSE_KWARGS.keys(), parse_args))
        progress = gr.Progress()

        for i, chat in enumerate(chats_list, start=1):
            try:
                parse_chats_pb_info = f'Parsing chats {i}/{len(chats_list)}'
                message_dicts = await cls.get_messages_from_chat(client, chat.chat, parse_chats_pb_info, **parse_kwargs)
                if len(message_dicts) == 0:
                    log_msg = f'Из чата {chat.chat_username} не было извлечено ни одного сообщения'
                    parse_result += log_msg + '\n'
                else:
                    cvs_path = cls.messages_to_csv(message_dicts)
                    cvs_paths.append(cvs_path)
                    log_msg = f'Успешный парсинг чата {chat.chat_username}, кол-во сообщений: {len(message_dicts)}'
                    parse_result += log_msg + '\n'
            except Exception as ex:
                log_msg = f'Ошибка при парсинге чата {chat.chat_username}, код ошибки: {ex}'
                parse_result += log_msg + '\n'

            progress(i / len(chats_list), desc=parse_chats_pb_info)
        return parse_result, cvs_paths

    @classmethod
    def messages_to_csv(cls, message_dicts: Collection[MESSAGE_DICT]) -> Path:
        df = pd.DataFrame.from_dict(message_dicts)
        chat_name = message_dicts[0].get('chat_name', '')
        cvs_path = cls.parse_results_dir / f'telegram_history_{chat_name}.csv'
        df.to_csv(cvs_path, index=False)
        return cvs_path

    @classmethod
    def zip_files(cls, file_paths: Collection[Path]) -> Path:
        zip_filepath = cls.parse_results_dir / 'parse_results_csv.zip'
        with zipfile.ZipFile(zip_filepath, 'w') as zipf:
            for file_path in file_paths:
                zipf.write(file_path, arcname=file_path)
        return zip_filepath

    @staticmethod
    def get_chats_info(chats_list: list[Chat]) -> str:
        chats_info = ''
        for i, chat in enumerate(chats_list, start=1):
            chats_info += f'{i}: ' + chat.get_chat_info() + '\n'
        return chats_info

    @staticmethod
    async def get_chat(client: TelegramClient, chat_username: str) -> types.TLObject:
        try:
            if client.is_connected():
                chat = await client.get_entity(chat_username)
            else:
                async with client:
                    chat = await client.get_entity(chat_username)
        except (errors.UsernameNotOccupiedError, errors.UsernameInvalidError) as ex:
            log_msg = f'Чат или канал {chat_username} не найден или введен неверно'
            raise errors.UsernameInvalidError(log_msg)
        except Exception as ex:
            log_msg = f'Ошибка при получении объекта чата, код ошибки: {ex}'
            raise Exception(log_msg)
        return chat

    @classmethod
    async def add_chat_to_chats_list(
        cls, 
        auth_state: AuthState,
        chats_usernames,
        chats_list: list[Chat],
        api_id: str,
        api_hash: str,
        ) -> str:

        if chats_usernames.strip() == '':
            return 'Не заданы адрес/адреса чатов для добавления'

        client = ClientConnector.get_client(auth_state.get_session(), api_id, api_hash)
        validation_result = await Validator.validate_auth(client)
        if not validation_result.is_valid:
            return 'Клиент не авторизован'

        for chat_username in chats_usernames.split():
            try:
                telethon_chat = await cls.get_chat(client, chat_username.strip())
                if not telethon_chat in chats_list:
                    chat = Chat.from_telethon_chat(telethon_chat, chat_username)
                    chats_list.append(chat)
                else:
                    log_msg = f'Чат {chat_username} уже есть в списке'
                    gr.Info(log_msg)
            except Exception as ex:
                log_msg = str(ex)
                gr.Info(log_msg)
        return cls.get_chats_info(chats_list)


Parser.parse_results_dir.mkdir(exist_ok=True)
