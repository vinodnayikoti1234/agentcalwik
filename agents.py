import streamlit as st
import json
import requests
import os
import wikipediaapi
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
# --------------------------------------------------
# OpenRouter Client
# --------------------------------------------------
client = OpenAI(
    api_key=os.getenv("api_key"),
    base_url="https://openrouter.ai/api/v1"
)

# --------------------------------------------------
# Tools
# --------------------------------------------------

def get_weather(city: str):
    try:
        url = f"https://wttr.in/{city}?format=%C+%t"
        response = requests.get(url)

        if response.status_code == 200:
            return f"The weather in {city} is {response.text}"

        return "Weather service unavailable"

    except Exception as e:
        return str(e)


def run_command(cmd: str):
    try:
        return str(os.system(cmd))
    except Exception as e:
        return str(e)


def calculator(expression: str):
    try:
        return str(eval(expression))
    except Exception as e:
        return f"Calculation Error: {e}"


def search_wikipedia(query: str):
    try:
        wiki = wikipediaapi.Wikipedia(
            user_agent="WikiAssistant",
            language="en"
        )

        page = wiki.page(query)

        if page.exists():
            return page.summary[:1000]

        return f"No article found for {query}"

    except Exception as e:
        return str(e)


available_tools = {
    "get_weather": get_weather,
    "run_command": run_command,
    "calculator": calculator,
    "search_wikipedia": search_wikipedia
}

# --------------------------------------------------
# Prompt
# --------------------------------------------------

SYSTEM_PROMPT = """
You are an AI Assistant.

Return JSON only.

Format:
{
    "step":"plan/action/output",
    "content":"text",
    "function":"tool_name",
    "input":"tool_input"
}

Available Tools:
- get_weather
- calculator
- search_wikipedia
- run_command

Always think step by step.
Use one step at a time.
"""

# --------------------------------------------------
# Streamlit UI
# --------------------------------------------------


st.set_page_config(
    page_title="AI Agent",
    page_icon="🤖",
    layout="wide"
)

st.title("🤖 AI Agent")

if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT
        }
    ]

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# Show old messages
for msg in st.session_state.chat_history:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# --------------------------------------------------
# User Input
# --------------------------------------------------

query = st.chat_input("Ask anything...")

if query:

    st.session_state.chat_history.append(
        {"role": "user", "content": query}
    )

    with st.chat_message("user"):
        st.markdown(query)

    st.session_state.messages.append(
        {"role": "user", "content": query}
    )

    with st.chat_message("assistant"):

        status = st.status(
            "🧠 Thinking...",
            expanded=True
        )

        final_answer = ""

        while True:

            response = client.chat.completions.create(
            model="google/gemini-3.5-flash",
            messages=st.session_state.messages,
            response_format={"type": "json_object"},
            max_tokens=1000
            )
            llm_response = response.choices[0].message.content
            
            
            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": llm_response
                }
            )

            parsed = json.loads(llm_response)

            step = parsed.get("step")

            # ---------------- PLAN ----------------

            if step == "plan":

                plan_text = parsed.get("content")

                status.write(f"🧠 {plan_text}")

                continue

            # ---------------- ACTION ----------------

            if step == "action":

                tool_name = parsed.get("function")
                tool_input = parsed.get("input")

                status.write(
                    f"🛠️ Using Tool: **{tool_name}**"
                )

                status.write(
                    f"📥 Input: `{tool_input}`"
                )

                status.write(
                    "⏳ Please wait..."
                )

                if tool_name in available_tools:

                    output = available_tools[tool_name](
                        tool_input
                    )

                    status.write(
                        f"✅ Tool Output: {output}"
                    )

                    observation = {
                        "step": "observe",
                        "output": output
                    }

                    st.session_state.messages.append(
                        {
                            "role": "user",
                            "content": json.dumps(observation)
                        }
                    )

                    continue

            # ---------------- OUTPUT ----------------

            if step == "output":

                final_answer = parsed.get("content")

                status.update(
                    label="✅ Completed",
                    state="complete"
                )

                st.markdown(final_answer)

                st.session_state.chat_history.append(
                    {
                        "role": "assistant",
                        "content": final_answer
                    }
                )

                break
