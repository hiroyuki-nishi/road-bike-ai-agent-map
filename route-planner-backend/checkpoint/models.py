import operator
from typing import Annotated

from langchain_core.messages import BaseMessage
from langchain_core.pydantic_v1 import BaseModel, Field


class State(BaseModel):
    query: str
    messages: Annotated[list[BaseMessage], operator.add] = Field([])
