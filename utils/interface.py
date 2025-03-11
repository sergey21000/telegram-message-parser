import gradio as gr

from utils.auth import AuthState, ClientConnector
from utils.components import Components, ComponentsFn
from utils.parser import Parser


def create_interface() -> gr.Blocks:
    auth_state = AuthState()
    auth_state.check_start_auth_status()

    # css = '.gradio-container {width: 60% !important}'
    css = '''
    .gradio-container {
        width: 70% !important;
        margin: 0 auto !important; /* Центрирование по горизонтали */
    }
    '''

    with gr.Blocks(css=css) as interface:
        gr.Markdown(Components.welcome_message_markdown)
        
        auth_state = gr.State(auth_state)
        chats_list = gr.State([])
        csv_names = gr.State([])

        dynamic_visible_components = ComponentsFn.get_dynamic_visible_components(auth_state.value, render=False)
        code, code_btn, password_2fa, password_2fa_btn, delete_session_btn = dynamic_visible_components

        with gr.Group():
            gr.Markdown('Авторизация')
            with gr.Row():
                with gr.Column():
                    session_type = Components.session_type_radio()
                    auth_status = Components.auth_status(value=auth_state.value.message)
                    with gr.Row():
                        auth_btn = Components.auth_btn()
                        delete_session_btn.render()
                    code.render()
                    code_btn.render()
                    password_2fa.render()
                    password_2fa_btn.render()

                with gr.Column():
                    api_id = Components.api_id()
                    api_hash = Components.api_hash()
                    phone_number = Components.phone_number()

        auth_btn.click(
            fn=ClientConnector.start_auth,
            inputs=[auth_state, api_id, api_hash],
            outputs=[auth_state],
        ).then(
            fn=ClientConnector.send_code,
            inputs=[auth_state, phone_number],
            outputs=[auth_state],
        ).then(
            fn=ComponentsFn.get_dynamic_visible_components,
            inputs=[auth_state],
            outputs=dynamic_visible_components,
        ).then(
            fn=ComponentsFn.update_status,
            inputs=[auth_state],
            outputs=[auth_status],
        )

        code_btn.click(
            fn=ClientConnector.verify_code,
            inputs=[auth_state, phone_number, code],
            outputs=[auth_state],
        ).then(
            fn=ComponentsFn.get_dynamic_visible_components,
            inputs=[auth_state],
            outputs=dynamic_visible_components,
        ).then(
            fn=ComponentsFn.update_status,
            inputs=[auth_state],
            outputs=[auth_status],
        )

        password_2fa_btn.click(
            fn=ClientConnector.verify_2fa,
            inputs=[auth_state, password_2fa],
            outputs=[auth_state],
        ).then(
            fn=ComponentsFn.get_dynamic_visible_components,
            inputs=[auth_state],
            outputs=dynamic_visible_components,
        ).then(
            fn=ComponentsFn.update_status,
            inputs=[auth_state],
            outputs=[auth_status],
        )

        delete_session_btn.click(
            fn=ComponentsFn.delete_session,
            inputs=[auth_state],
            outputs=None,
        ).then(
            fn=ComponentsFn.get_dynamic_visible_components,
            inputs=[auth_state],
            outputs=dynamic_visible_components,
        ).then(
            fn=ComponentsFn.update_status,
            inputs=[auth_state],
            outputs=[auth_status],
        )

        session_type.change(
            fn=ComponentsFn.update_auth_state_session_type,
            inputs=[auth_state, session_type],
            outputs=None,
        )


        with gr.Group():
            gr.Markdown('Парсинг')
            with gr.Row():
                with gr.Column():
                    with gr.Group():
                        gr.Markdown('Чаты для парсинга')
                        chats_usernames = Components.chats_usernames()
                        add_chat_btn = Components.add_chat_btn()
                        chats_list_status = Components.chats_list_status()
                with gr.Column():
                    with gr.Group():
                        gr.Markdown('Параметры парсинга')
                        parse_args = Components.get_parse_args()
                with gr.Column():
                    with gr.Group():
                        gr.Markdown('Результаты парсинга')
                        start_parse_btn = Components.start_parse_btn()
                        parse_status = Components.parse_status()
                        download_btn = Components.download_btn()

        add_chat_btn.click(
            fn=Parser.add_chat_to_chats_list,
            inputs=[auth_state, chats_usernames, chats_list, api_id, api_hash],
            outputs=[chats_list_status],
        )

        start_parse_btn.click(
            fn=Parser.parse_chats,
            inputs=[auth_state, chats_list, api_id, api_hash, *parse_args],
            outputs=[parse_status, csv_names],
        ).then(
            fn=ComponentsFn.update_download_btn,
            inputs=[csv_names],
            outputs=[download_btn],
        )

    return interface
