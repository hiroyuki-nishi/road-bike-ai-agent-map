import operator
from typing import Annotated

from langchain_core.pydantic_v1 import BaseModel, Field


class State(BaseModel):
    query: str = Field(..., description="ユーザーからの質問")
    current_role: str = Field("", description="選択された回答ロール")
    messages: Annotated[list[str], operator.add] = Field([], description="回答履歴")
    current_judge: bool = Field(False, description="品質のチェックの結果")
    judgement_reason: str = Field("", description="品質チェックの判定理由")


