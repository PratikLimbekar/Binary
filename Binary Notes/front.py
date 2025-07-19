import streamlit as st
import numpy as np
from geminifornotes import getairesponse
from datetime import datetime
import os

st.title("Binary Notes")
st.subheader("A Brain, Note-Storage for Binary")

st.sidebar.title("Binary Notes")
st.sidebar.button("Developer Link")
tab1, tab2 = st.tabs(["Chat", "Notes"])

chatlog = open(f"chatlogs\{datetime.today().strftime('%Y-%m-%d')}.txt", 'a')

with tab1:
    with st.chat_message("user"):
        st.write("Hello there!")

    prompt = []

    prompt = st.chat_input("Say something")
    if prompt:
        chatlog.write(f"\n --- {datetime.today().strftime('%Y-%m-%d')} \n")
        with st.chat_message("user"):
            st.write(prompt)
            chatlog.write('\n' + "User: "+ prompt + '\n')
        with st.chat_message("assistant"):
            answer = getairesponse(prompt)
            st.write("Binary: ")
            st.write(answer)
            chatlog.write("Binary: "+ answer + '\n')
chatlog.close()

with tab2:
    for filename in os.listdir('chatlogs'):
        with open(f"chatlogs/{filename}", 'r') as chatlog:
            content = chatlog.read()
            logsperdate = content.split("--- ")
            for section in logsperdate:
                lines = section.strip().split('\n')
                date = lines[0]
                messages = '\n'.join(lines)


    with st.expander("Chat Logs"):
        for filename in os.listdir('chatlogs'):
            with open(f"chatlogs/{filename}", 'r') as chatlog:
                # content = chatlog.read()
                # logsperdate = content.split("---")
                # for section in logsperdate:
                #     lines = section.strip().split('\n')
                #     date = lines[0]
                #     messages = '\n'.join(lines)
                # with st.expander(f"Chat Logs {date}"):
                #     st.subheader(date)
                #     st.write(messages)
                content = chatlog.read()
                with st.expander(filename):
                    st.write(content)
                # st.sidebar.button(label=messages.strip().split('\n')[1])
                
    chatlog.close()
    # # chatcontent = chatlog.read()
    # st.code(messages)