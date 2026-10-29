"""Part 3-II.4 conversation chain: buffer memory, history-aware retrieval, context-only answers."""
from dataclasses import dataclass
import os

from dotenv import load_dotenv
from rag.embeddings import official_client
from shared.config import CONFIG, ROOT
from shared.contracts import SearchHit

CONDENSE_PROMPT = ('Rewrite the follow-up question as one standalone question. Use the chat history '
                   'only to resolve references such as "it" or "that part". Keep the language of the '
                   'question. Return only the rewritten question.')
ANSWER_PROMPT = ('Answer the question using only the numbered context passages. Cite the passages '
                 'you use, for example [1]. If the passages do not contain the answer, say that the '
                 'documents do not cover it instead of guessing. Answer in the language of the question.')


def chat_model() -> str:
    load_dotenv(ROOT / '.env')
    model = os.getenv('OPENAI_CHAT_MODEL', '').strip()
    if not model:
        raise ValueError('Set OPENAI_CHAT_MODEL in root .env.')
    return model


class OpenAIChat:
    """Official OpenAI Chat Completions with the model's default sampling."""

    def __init__(self, model: str, *, client=None):
        self.model = model
        self.client = client or official_client()

    def complete(self, messages: list[dict]) -> str:
        # gpt-6-luna rejects temperature=0 (evidence/c-step5), so no sampling options are sent.
        response = self.client.chat.completions.create(model=self.model, messages=messages)
        text = (response.choices[0].message.content or '').strip()
        if not text:
            raise ValueError('The chat model returned an empty answer.')
        return text


@dataclass(frozen=True)
class ChainResult:
    answer: str
    standalone_question: str
    hits: list[SearchHit]


class BufferMemory:
    """Full chat buffer for one session: the role of LangChain's ConversationBufferMemory.
    Kept here because LangChain's memory classes are deprecated (langchain-core 1.6.4 also
    deprecated InMemoryChatMessageHistory)."""

    def __init__(self):
        self.messages: list[dict] = []

    def add_turn(self, question: str, answer: str) -> None:
        self.messages += [{'role': 'user', 'content': question},
                          {'role': 'assistant', 'content': answer}]


def format_history(messages: list[dict]) -> str:
    return '\n'.join(f"{'User' if m['role'] == 'user' else 'Assistant'}: {m['content']}"
                     for m in messages)


def format_context(hits: list[SearchHit]) -> str:
    blocks = []
    for number, hit in enumerate(hits, start=1):
        page = f', page {hit.chunk.page}' if hit.chunk.page is not None else ''
        blocks.append(f'[{number}] ({hit.chunk.source}{page})\n{hit.chunk.text}')
    return '\n\n'.join(blocks)


class ConversationChain:
    def __init__(self, llm, vectorstore, k: int):
        if k <= 0:
            raise ValueError('k must be positive.')
        self.llm, self.vectorstore, self.k = llm, vectorstore, k
        self.sessions: dict[str, BufferMemory] = {}

    def memory(self, session_id: str) -> BufferMemory:
        return self.sessions.setdefault(session_id, BufferMemory())

    def ask(self, question: str, session_id: str) -> ChainResult:
        question = question.strip()
        if not question:
            raise ValueError('Question must not be empty.')
        memory = self.memory(session_id)
        standalone = question
        if memory.messages:
            standalone = self.llm.complete([
                {'role': 'system', 'content': CONDENSE_PROMPT},
                {'role': 'user', 'content': f'Chat history:\n{format_history(memory.messages)}'
                                            f'\n\nFollow-up question: {question}'},
            ])
        hits = self.vectorstore.search(standalone, self.k)
        answer = self.llm.complete([
            {'role': 'system', 'content': ANSWER_PROMPT},
            {'role': 'user', 'content': f'Context:\n{format_context(hits)}\n\nQuestion: {standalone}'},
        ])
        # Memory changes only after a complete turn, so a failed call leaves no half-turn behind.
        memory.add_turn(question, answer)
        return ChainResult(answer, standalone, hits)


def create_conversation_chain(llm, vectorstore, k: int = CONFIG['rag']['retrieval_k']) -> ConversationChain:
    return ConversationChain(llm, vectorstore, k)
