import logging
import os
from typing import Any

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import ConfigurableField
from langchain_openai import ChatOpenAI
from langgraph.constants import END
from langgraph.graph import StateGraph
from dotenv import load_dotenv
from logging import getLogger
from IPython.display import Image

from roles import ROLES
from models import State, Judgment


def selection_node(state: State) -> dict[str, Any]:
    query = state.query
    role_options = "\n".join({f"{k}.{v['name']}: {v['description']}" for k, v in ROLES.items()})
    prompt = ChatPromptTemplate.from_template(
        """質問を分析し、最も適切な回答担当ロールを選択してください。
        
        選択肢：
        {role_options}
        
        回答は選択肢の番号（１、２、または３）のみを返してください。
        
        質問：{query}
        """.strip()
    )
    # 選択肢の番号のみを返すことを期待したいため、max_tokensを1に変更
    chain = prompt | llm.with_config(configurable=dict(max_tokens=1)) | StrOutputParser()
    role_number = chain.invoke({"role_options": role_options, "query": query})
    selected_role = ROLES[role_number.strip()]["name"]
    return {"current_role": selected_role}

def answering_node(state: State) -> dict[str, Any]:
    query = state.query
    role = state.current_role
    role_details = "\n".join([f"- {v['name']}: {v['details']}" for v in ROLES.values()])
    prompt = ChatPromptTemplate.from_template(
        """あなたは{role}として回答してください。以下の質問に対して、あなたの役割に基づいた適切な回答を提供してください。
        
        役割の詳細：
        {role_details}
        
        質問：{query}
        
        回答：""".strip()
    )
    chain = prompt | llm | StrOutputParser()
    answer = chain.invoke({"role": role, "role_details": role_details, "query": query})
    return {"messages": [answer]}

def check_node(state: State) -> dict[str, Any]:
    query = state.query
    answer = state.messages[-1]
    prompt = ChatPromptTemplate.from_template(
        """以下の回答の品質をチェックし、問題がある場合は'False'、問題がない場合は
        'True'を回答してください。また、その判断理由も説明してください。
        
        ユーザーからの質問：{query}
        
        質問：{query}
        
        回答：{answer}
        
        回答の品質が高い場合は「Yes」、低い場合は「No」を返してください。
        """.strip()
    )
    chain = prompt | llm.with_structured_output(Judgment)
    r: Judgment = chain.invoke({"query": query, "answer": answer})
    return {
        "current_judge": r.judge,
        "judgement_reason": r.reason
    }


"""

          +----------------+
          |    State       |
          | query          |
          | current_role   |
          | messages       |
          | current_judge  |
          | judgement_reason |
          +----------------+
                  |
  +---------------+-----------------------------+
  |                        |                    |
+------------+       +------------+       +------------+
| selection  | ---+->| answering  |<----+ |   check     |
| (役割を設定)|        | (回答を生成)|       | (品質チェック)|
+------------+      +------------+         +------------+
      |                      ^                   ^
      +-----------+----------+------------------+
                              |
                         (終点ノード)
"""

logging.basicConfig(level=logging.INFO)
logger = getLogger(__name__)
logger.info("----------START----------")
load_dotenv()
llm = ChatOpenAI(
    model="gpt-4o",
    api_key=os.environ['OPENAI_API_KEY'],
    temperature=0.0
)
# 後からmax_tokensの値を変更できるように、変更可能なフィールドを宣言
llm = llm.configurable_fields(max_tokens=ConfigurableField(id="max_tokens"))

# NOTE
# StateGraphには、input_schema, output_schema, state_schemaなどを指定することができます。
# 要するに、どういったデータ型をワークフローで扱うかという定義設定
workflow = StateGraph(State)

workflow.add_node("selection", selection_node)
workflow.add_node("answering", answering_node)
workflow.add_node("check", check_node)

workflow.set_entry_point("selection")
# selectionノートからansweringノートにエッジを張る
workflow.add_edge("selection", "answering")
workflow.add_edge("answering", "check")

workflow.add_conditional_edges(
    "check",
    lambda state: state.current_judge,
    {True: END, False: "selection"}
)
compiled = workflow.compile()
Image(compiled.get_graph().draw_png())

initial_state = State(query="生成AIについて教えてください")
result = compiled.invoke(initial_state)
logger.info(result)
logger.info("----------END----------")
