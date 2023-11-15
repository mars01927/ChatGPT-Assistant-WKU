import os.path

from libs.helper import *
import streamlit as st
import uuid
import pandas as pd
import openai
from requests.models import ChunkedEncodingError
from streamlit.components import v1
from voice_toolkit import voice_toolkit

if "apibase" in st.secrets:
    openai.api_base = st.secrets["apibase"]
else:
    openai.api_base = "https://api.openai.com/v1"

st.set_page_config(page_title="WKU CPS Department Assistant", layout="wide", page_icon="🤖")

st.markdown(css_code, unsafe_allow_html=True)

if "initial_settings" not in st.session_state:
    # 历史聊天窗口
    st.session_state["path"] = "history_chats_file"
    st.session_state["history_chats"] = get_history_chats(st.session_state["path"])
    # ss参数初始化
    st.session_state["delete_dict"] = {}
    st.session_state["delete_count"] = 0
    st.session_state["voice_flag"] = ""
    st.session_state["user_voice_value"] = ""
    st.session_state["error_info"] = ""
    st.session_state["current_chat_index"] = 0
    st.session_state["user_input_content"] = ""

    if os.path.exists("./set.json"):
        with open("./set.json", "r", encoding="utf-8") as f:
            data_set = json.load(f)
        for key, value in data_set.items():
            st.session_state[key] = value

    st.session_state["initial_settings"] = True

with st.sidebar:
    st.markdown("# 🤖 Chat")
    chat_container = st.container()
    with chat_container:
        current_chat = st.radio(
            label="History",
            format_func=lambda x: x.split("_")[0] if "_" in x else x,
            options=st.session_state["history_chats"],
            label_visibility="collapsed",
            index=st.session_state["current_chat_index"],
            key="current_chat"
            + st.session_state["history_chats"][st.session_state["current_chat_index"]],
            # on_change=current_chat_callback  # 此处不适合用回调，无法识别到窗口增减的变动
        )
    st.write("---")



def write_data(new_chat_name=current_chat):
    if "apikey" in st.secrets:
        st.session_state["paras"] = {
            "temperature": st.session_state["temperature" + current_chat],
            "top_p": st.session_state["top_p" + current_chat],
            "presence_penalty": st.session_state["presence_penalty" + current_chat],
            "frequency_penalty": st.session_state["frequency_penalty" + current_chat],
        }
        st.session_state["contexts"] = {
            "context_select": st.session_state["context_select" + current_chat],
            "context_input": st.session_state["context_input" + current_chat],
            "context_level": st.session_state["context_level" + current_chat],
        }
        save_data(
            st.session_state["path"],
            new_chat_name,
            st.session_state["history" + current_chat],
            st.session_state["paras"],
            st.session_state["contexts"],
        )


def reset_chat_name_fun(chat_name):
    chat_name = chat_name + "_" + str(uuid.uuid4())
    new_name = filename_correction(chat_name)
    current_chat_index = st.session_state["history_chats"].index(current_chat)
    st.session_state["history_chats"][current_chat_index] = new_name
    st.session_state["current_chat_index"] = current_chat_index

    write_data(new_name)

    st.session_state["history" + new_name] = st.session_state["history" + current_chat]
    for item in [
        "context_select",
        "context_input",
        "context_level",
        *initial_content_all["paras"],
    ]:
        st.session_state[item + new_name + "value"] = st.session_state[
            item + current_chat + "value"
        ]
    remove_data(st.session_state["path"], current_chat)


def create_chat_fun():
    st.session_state["history_chats"] = [
        "New Chat_" + str(uuid.uuid4())
    ] + st.session_state["history_chats"]
    st.session_state["current_chat_index"] = 0


def delete_chat_fun():
    if len(st.session_state["history_chats"]) == 1:
        chat_init = "New Chat_" + str(uuid.uuid4())
        st.session_state["history_chats"].append(chat_init)
    pre_chat_index = st.session_state["history_chats"].index(current_chat)
    if pre_chat_index > 0:
        st.session_state["current_chat_index"] = (
            st.session_state["history_chats"].index(current_chat) - 1
        )
    else:
        st.session_state["current_chat_index"] = 0
    st.session_state["history_chats"].remove(current_chat)
    remove_data(st.session_state["path"], current_chat)


with st.sidebar:
    c1, c2 = st.columns(2)
    create_chat_button = c1.button(
        "new", use_container_width=True, key="create_chat_button"
    )
    if create_chat_button:
        create_chat_fun()
        st.experimental_rerun()

    delete_chat_button = c2.button(
        "delete", use_container_width=True, key="delete_chat_button"
    )
    if delete_chat_button:
        delete_chat_fun()
        st.experimental_rerun()

with st.sidebar:
    if ("set_chat_name" in st.session_state) and st.session_state[
        "set_chat_name"
    ] != "":
        reset_chat_name_fun(st.session_state["set_chat_name"])
        st.session_state["set_chat_name"] = ""
        st.experimental_rerun()

    st.write("\n")
    st.write("\n")
    st.text_input("set the name of window：", key="set_chat_name", placeholder="Click to enter")
    st.selectbox(
        "Choose Model：", index=0, options=["gpt-3.5-turbo", "gpt-4"], key="select_model"
    )
    st.write("\n")
    st.caption(
        """
    - Made by WKU CPS Department
    - Zhen Ma, Hongtao Lu, Zike Deng, Chi Zhang
    """
    )


if "history" + current_chat not in st.session_state:
    for key, value in load_data(st.session_state["path"], current_chat).items():
        if key == "history":
            st.session_state[key + current_chat] = value
        else:
            for k, v in value.items():
                st.session_state[k + current_chat + "value"] = v


container_show_messages = st.container()
container_show_messages.write("")

with container_show_messages:
    if st.session_state["history" + current_chat]:
        show_messages(current_chat, st.session_state["history" + current_chat])


if any(st.session_state["delete_dict"].values()):
    for key, value in st.session_state["delete_dict"].items():
        try:
            deleteCount = value.get("deleteCount")
        except AttributeError:
            deleteCount = None
        if deleteCount == st.session_state["delete_count"]:
            delete_keys = key
            st.session_state["delete_count"] = deleteCount + 1
            delete_current_chat, idr = delete_keys.split(">")
            df_history_tem = pd.DataFrame(
                st.session_state["history" + delete_current_chat]
            )
            df_history_tem.drop(
                index=df_history_tem.query("role=='user'").iloc[[int(idr)], :].index,
                inplace=True,
            )
            df_history_tem.drop(
                index=df_history_tem.query("role=='assistant'")
                .iloc[[int(idr)], :]
                .index,
                inplace=True,
            )
            st.session_state["history" + delete_current_chat] = df_history_tem.to_dict(
                "records"
            )
            write_data()
            st.experimental_rerun()


def callback_fun(arg):
    # 连续快速点击新建与删除会触发错误回调，增加判断
    if ("history" + current_chat in st.session_state) and (
        "frequency_penalty" + current_chat in st.session_state
    ):
        write_data()
        st.session_state[arg + current_chat + "value"] = st.session_state[
            arg + current_chat
        ]


def clear_button_callback():
    st.session_state["history" + current_chat] = []
    write_data()


def delete_all_chat_button_callback():
    if "apikey" in st.secrets:
        folder_path = st.session_state["path"]
        file_list = os.listdir(folder_path)
        for file_name in file_list:
            file_path = os.path.join(folder_path, file_name)
            if file_name.endswith(".json") and os.path.isfile(file_path):
                os.remove(file_path)
    st.session_state["current_chat_index"] = 0
    st.session_state["history_chats"] = ["New Chat_" + str(uuid.uuid4())]


def save_set(arg):
    st.session_state[arg + "_value"] = st.session_state[arg]
    if "apikey" in st.secrets:
        with open("./set.json", "w", encoding="utf-8") as f:
            json.dump(
                {
                    "open_text_toolkit_value": st.session_state["open_text_toolkit"],
                    "open_voice_toolkit_value": st.session_state["open_voice_toolkit"],
                },
                f,
            )



area_user_svg = st.empty()
area_user_content = st.empty()

area_gpt_svg = st.empty()
area_gpt_content = st.empty()

area_error = st.empty()

st.write("\n")
st.header("WKU CPS Department Assistant")
tap_input, tap_context, tap_model, tab_func = st.tabs(
    ["💬 Chat", "🗒️ Set", "⚙️ Model", "🛠️ Function"]
)

with tap_context:
    set_context_list = list(set_context_all.keys())
    context_select_index = set_context_list.index(
        st.session_state["context_select" + current_chat + "value"]
    )
    st.selectbox(
        label="Choose Prompt",
        options=set_context_list,
        key="context_select" + current_chat,
        index=context_select_index,
        on_change=callback_fun,
        args=("context_select",),
    )
    st.caption(set_context_all[st.session_state["context_select" + current_chat]])

    st.text_area(
        label="Customize Prompt：",
        key="context_input" + current_chat,
        value=st.session_state["context_input" + current_chat + "value"],
        on_change=callback_fun,
        args=("context_input",),
    )

with tap_model:
    st.markdown("OpenAI API Key (optional)")
    st.text_input(
        "OpenAI API Key (optional)",
        type="password",
        key="apikey_input",
        label_visibility="collapsed",
    )
    st.caption(
        "This key is only valid on the current webpage and has a higher priority than the configuration in Secrets."
    )

    st.markdown("Including conversation times：")
    st.slider(
        "Context Level",
        0,
        10,
        st.session_state["context_level" + current_chat + "value"],
        1,
        on_change=callback_fun,
        key="context_level" + current_chat,
        args=("context_level",),
        help="Indicates the number of historical conversations included in each conversation, and the default content is not counted.",
    )

    st.markdown("Model parameters:")
    st.slider(
        "Temperature",
        0.0,
        2.0,
        st.session_state["temperature" + current_chat + "value"],
        0.1,
        help="""What sampling temperature should be used between 0 and 2? A higher value (such as 0.8) will make the output more random, while a lower value (such as 0.2) will make it more concentrated and deterministic.
We generally recommend only changing this parameter or top_ One of the p parameters, rather than changing both at the same time.""",
        on_change=callback_fun,
        key="temperature" + current_chat,
        args=("temperature",),
    )
    st.slider(
        "Top P",
        0.1,
        1.0,
        st.session_state["top_p" + current_chat + "value"],
        0.1,
        help="""An alternative method of sampling using temperature is called "core probability based" sampling. In this method, the model considers the top with the highest probability_ Predicted results for p markers.
Therefore, when the parameter is 0.1, only markers including the top 10% probability mass will be considered. We generally recommend changing only one of these parameters or sampling temperature parameters, rather than changing both at the same time.""",
        on_change=callback_fun,
        key="top_p" + current_chat,
        args=("top_p",),
    )
    st.slider(
        "Presence Penalty",
        -2.0,
        2.0,
        st.session_state["presence_penalty" + current_chat + "value"],
        0.1,
        help="""The value range of this parameter is -2.0 to 2.0. A positive value will penalize the new tag based on whether it appears in the currently generated text, thereby increasing the likelihood of the model discussing new topics.""",
        on_change=callback_fun,
        key="presence_penalty" + current_chat,
        args=("presence_penalty",),
    )
    st.slider(
        "Frequency Penalty",
        -2.0,
        2.0,
        st.session_state["frequency_penalty" + current_chat + "value"],
        0.1,
        help="""The value range of this parameter is -2.0 to 2.0. A positive value will penalize the new tag based on its existing frequency in the currently generated text, thereby reducing the possibility of the model directly repeating the same statement.""",
        on_change=callback_fun,
        key="frequency_penalty" + current_chat,
        args=("frequency_penalty",),
    )
with tab_func:
    c1, c2, c3 = st.columns(3)
    with c1:
        st.button("Clear chat records", use_container_width=True, on_click=clear_button_callback)
    with c2:
        btn = st.download_button(
            label="Export chat records",
            data=download_history(st.session_state["history" + current_chat]),
            file_name=f'{current_chat.split("_")[0]}.md',
            mime="text/markdown",
            use_container_width=True,
        )
    with c3:
        st.button(
            "Delete all windows", use_container_width=True, on_click=delete_all_chat_button_callback
        )

    st.write("\n")
    st.markdown("custom function：")
    c1, c2 = st.columns(2)
    with c1:
        if "open_text_toolkit_value" in st.session_state:
            default = st.session_state["open_text_toolkit_value"]
        else:
            default = True
        st.checkbox(
            "Enable functional components under text",
            value=default,
            key="open_text_toolkit",
            on_change=save_set,
            args=("open_text_toolkit",),
        )
    with c2:
        if "open_voice_toolkit_value" in st.session_state:
            default = st.session_state["open_voice_toolkit_value"]
        else:
            default = True
        st.checkbox(
            "Enable voice input component",
            value=default,
            key="open_voice_toolkit",
            on_change=save_set,
            args=("open_voice_toolkit",),
        )

with tap_input:

    def input_callback():
        if st.session_state["user_input_area"] != "":

            user_input_content = st.session_state["user_input_area"]
            df_history = pd.DataFrame(st.session_state["history" + current_chat])
            if df_history.empty or len(df_history.query('role!="system"')) == 0:
                new_name = extract_chars(user_input_content, 18)
                reset_chat_name_fun(new_name)

    with st.form("input_form", clear_on_submit=True):
        user_input = st.text_area(
            "**input：**",
            key="user_input_area",
            help="The content will be displayed on the page in Markdown format. It is recommended to follow relevant language specifications, which is also beneficial for GPT to read correctly, such as:"
            "\n- Code blocks are written within three backquotes and labeled with language types"
            "\n- Write content or regular expressions that start with an English colon within single back quotes",
            value=st.session_state["user_voice_value"],
        )
        submitted = st.form_submit_button(
            "Submit", use_container_width=True, on_click=input_callback
        )
    if submitted:
        st.session_state["user_input_content"] = user_input
        st.session_state["user_voice_value"] = ""
        st.experimental_rerun()

    if (
        "open_voice_toolkit_value" not in st.session_state
        or st.session_state["open_voice_toolkit_value"]
    ):

        vocie_result = voice_toolkit()

        if (
            vocie_result and vocie_result["voice_result"]["flag"] == "interim"
        ) or st.session_state["voice_flag"] == "interim":
            st.session_state["voice_flag"] = "interim"
            st.session_state["user_voice_value"] = vocie_result["voice_result"]["value"]
            if vocie_result["voice_result"]["flag"] == "final":
                st.session_state["voice_flag"] = "final"
                st.experimental_rerun()


def get_model_input():

    context_level = st.session_state["context_level" + current_chat]
    history = get_history_input(
        st.session_state["history" + current_chat], context_level
    ) + [{"role": "user", "content": st.session_state["pre_user_input_content"]}]
    for ctx in [
        st.session_state["context_input" + current_chat],
        set_context_all[st.session_state["context_select" + current_chat]],
    ]:
        if ctx != "":
            history = [{"role": "system", "content": ctx}] + history

    paras = {
        "temperature": st.session_state["temperature" + current_chat],
        "top_p": st.session_state["top_p" + current_chat],
        "presence_penalty": st.session_state["presence_penalty" + current_chat],
        "frequency_penalty": st.session_state["frequency_penalty" + current_chat],
    }
    return history, paras


if st.session_state["user_input_content"] != "":
    if "r" in st.session_state:
        st.session_state.pop("r")
        st.session_state[current_chat + "report"] = ""
    st.session_state["pre_user_input_content"] = st.session_state["user_input_content"]
    st.session_state["user_input_content"] = ""

    show_each_message(
        st.session_state["pre_user_input_content"],
        "user",
        "tem",
        [area_user_svg.markdown, area_user_content.markdown],
    )

    history_need_input, paras_need_input = get_model_input()

    with st.spinner("🤔"):
        try:
            if apikey := st.session_state["apikey_input"]:
                openai.api_key = apikey

            elif "apikey_tem" in st.secrets:
                openai.api_key = st.secrets["apikey_tem"]
            # 注：当st.secrets中配置apikey后将会留存聊天记录，即使未使用此apikey
            else:
                openai.api_key = st.secrets["apikey"]
            r = openai.ChatCompletion.create(
                model=st.session_state["select_model"],
                messages=history_need_input,
                stream=True,
                **paras_need_input,
            )
        except (FileNotFoundError, KeyError):
            area_error.error(
                "The OpenAI API Key is missing. Please configure Secrets or temporarily configure it in the model options."
            )
        except openai.error.AuthenticationError:
            area_error.error("Invalid OpenAI API Key.")
        except openai.error.APIConnectionError as e:
            area_error.error("Connection timed out, please try again. Error reported:   \n" + str(e.args[0]))
        except openai.error.InvalidRequestError as e:
            area_error.error("Invalid request, please try again. Error reported:   \n" + str(e.args[0]))
        except openai.error.RateLimitError as e:
            area_error.error("Request restricted. Error reported:   \n" + str(e.args[0]))
        else:
            st.session_state["chat_of_r"] = current_chat
            st.session_state["r"] = r
            st.experimental_rerun()

if ("r" in st.session_state) and (current_chat == st.session_state["chat_of_r"]):
    if current_chat + "report" not in st.session_state:
        st.session_state[current_chat + "report"] = ""
    try:
        for e in st.session_state["r"]:
            if "content" in e["choices"][0]["delta"]:
                st.session_state[current_chat + "report"] += e["choices"][0]["delta"][
                    "content"
                ]
                show_each_message(
                    st.session_state["pre_user_input_content"],
                    "user",
                    "tem",
                    [area_user_svg.markdown, area_user_content.markdown],
                )
                show_each_message(
                    st.session_state[current_chat + "report"],
                    "assistant",
                    "tem",
                    [area_gpt_svg.markdown, area_gpt_content.markdown],
                )
    except ChunkedEncodingError:
        area_error.error("The network condition is not good. Please refresh the page and try again.")
    except Exception:
        pass
    else:

        st.session_state["history" + current_chat].append(
            {"role": "user", "content": st.session_state["pre_user_input_content"]}
        )
        st.session_state["history" + current_chat].append(
            {"role": "assistant", "content": st.session_state[current_chat + "report"]}
        )
        write_data()

    if current_chat + "report" in st.session_state:
        st.session_state.pop(current_chat + "report")
    if "r" in st.session_state:
        st.session_state.pop("r")
        st.experimental_rerun()

# 添加事件监听
v1.html(js_code, height=0)

gif_path = "https://i.postimg.cc/sDkMbr7s/bear.gif"

gif_html = f"""
    <div style="text-align: center; margin-top: -50px;">  
        <img src="{gif_path}" style="width: 18%;">
    </div>
"""

st.markdown(gif_html, unsafe_allow_html=True)




