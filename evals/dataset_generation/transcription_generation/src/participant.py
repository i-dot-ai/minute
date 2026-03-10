from common.llm.client import ChatBot, FastOrBestLLM, create_default_chatbot
from pydantic import BaseModel

class ChatEntry(BaseModel):
    role: str
    text: str   


class Participant:
    def __init__(self, chatbot:ChatBot | None = None) -> None:
        self.history : list[ChatEntry] = []
        self.chatbot= chatbot or create_default_chatbot(FastOrBestLLM.FAST) 
 
    def add_to_history(self, entry :ChatEntry):
        self.history.append(entry)


 
class Actor(Participant):
    def __init__(self, id: str, chatbot:ChatBot | None = None) -> None:
        super().__init__(chatbot)
        self.id = id

    async def reply(self) -> str:
        return await self.chatbot.chat(self.history)

    def __str__(self) -> str:
        return f"Actor {self.id}"   



   
    
 

      

