from typing import Any

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import ConfigurableField
from langchain_openai import ChatOpenAI
from langgraph.constants import END
from langgraph.graph import StateGraph

from example.roles import ROLES
from example.state import State

def selection_node(state: State) -> dict[str, Any]:
    query = state.query
    role_options = "\n".join({f"{k}.{v['name']}: {v['description']}" for k, v in ROLES.items()})
    prompt = ChatPromptTemplate.from_template(
        f"""質問を分析し、最も適切な回答担当ロールを選択してください。
        
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

    # ユーザーからの質問内容と選択されたロールをもとに回答を生成するロジック
    generated_message = "" # TODO
    return {"messages": [generated_message]}

def check_node(state: State) -> dict[str, Any]:
    query = state.query
    current_message = state.messages[-1]
    # 回答の品質をチェックするロジック
    judge = False # TODO
    reason = "" # TODO
    return {"current_judge": judge, "judgement_reason": reason}


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

llm = ChatOpenAI(model="gpt-4o", temperature=0.0)
# 後からmax_tokensの値を変更できるように、変更可能なフィールドを宣言
llm = llm.configurable_fields(max_tokens=ConfigurableField(id="max_tokens"))

# NOTE
# StateGraphには、input_schema, output_schema, state_schemaなどを指定することができます。
# 要するに、どういったデータ型をワークフローで扱うかという定義設定
workflow = StateGraph(State)
workflow.set_entry_point("selection")
# selectionノートからansweringノートにエッジを張る
workflow.add_edge("selection", "answering")

workflow.add_conditional_edges(
    "check",
    lambda state: state.current_judge,
    {True: END, False: "selection"}
)
compiled = workflow.compile()

initial_state = State(query="ユーザーからの質問内容")
result = compiled.invoke(initial_state)