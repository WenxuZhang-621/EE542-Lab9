"""Conversation chain logic with a scripted LLM and store; no API calls."""
from types import SimpleNamespace as NS
from unittest.mock import Mock
import unittest
from rag.chain import OpenAIChat, create_conversation_chain
from shared.contracts import Chunk, SearchHit


class ScriptedLLM:
    def __init__(self, *replies):
        self.replies, self.calls = list(replies), []

    def complete(self, messages):
        self.calls.append(messages)
        return self.replies.pop(0)


class RecordingStore:
    def __init__(self):
        self.queries = []

    def search(self, question, k):
        self.queries.append((question, k))
        return [SearchHit(Chunk('c1', 'Chunks have size 500.', 'lab.pdf', 4), 0.9)]


class ChainTests(unittest.TestCase):
    def test_first_turn_answers_from_retrieved_context(self):
        llm, store = ScriptedLLM('Size 500 [1].'), RecordingStore()
        chain = create_conversation_chain(llm, store, k=3)
        result = chain.ask(' What chunk size? ', 's1')
        self.assertEqual(result.answer, 'Size 500 [1].')
        self.assertEqual(store.queries, [('What chunk size?', 3)])
        self.assertEqual(len(llm.calls), 1)  # Empty history: no rewrite call.
        prompt = llm.calls[0][1]['content']
        self.assertIn('[1] (lab.pdf, page 4)\nChunks have size 500.', prompt)
        self.assertIn('Question: What chunk size?', prompt)
        self.assertEqual(chain.memory('s1').messages,
                         [{'role': 'user', 'content': 'What chunk size?'},
                          {'role': 'assistant', 'content': 'Size 500 [1].'}])

    def test_follow_up_is_rewritten_with_history_before_retrieval(self):
        llm = ScriptedLLM('Size 500 [1].', 'What overlap is used between chunks?', 'Overlap 100 [1].')
        store = RecordingStore()
        chain = create_conversation_chain(llm, store)
        chain.ask('What chunk size?', 's1')
        result = chain.ask('And the overlap?', 's1')
        self.assertEqual(result.standalone_question, 'What overlap is used between chunks?')
        self.assertEqual(store.queries[-1][0], 'What overlap is used between chunks?')
        rewrite = llm.calls[1][1]['content']
        self.assertIn('User: What chunk size?\nAssistant: Size 500 [1].', rewrite)
        self.assertIn('Follow-up question: And the overlap?', rewrite)
        self.assertEqual(len(chain.memory('s1').messages), 4)

    def test_sessions_are_isolated(self):
        llm = ScriptedLLM('A1', 'A2')
        chain = create_conversation_chain(llm, RecordingStore())
        chain.ask('Q1', 's1')
        result = chain.ask('Q2', 's2')
        self.assertEqual(result.standalone_question, 'Q2')
        self.assertEqual(len(llm.calls), 2)
        self.assertEqual(len(chain.memory('s2').messages), 2)

    def test_failed_turn_is_not_remembered_and_empty_question_rejected(self):
        class FailingStore:
            def search(self, question, k):
                raise RuntimeError('simulated API failure')
        chain = create_conversation_chain(ScriptedLLM(), FailingStore())
        with self.assertRaises(RuntimeError):
            chain.ask('Q', 's1')
        self.assertEqual(chain.memory('s1').messages, [])
        with self.assertRaises(ValueError):
            chain.ask('   ', 's1')

    def test_openai_chat_uses_default_sampling(self):
        client = Mock()
        client.chat.completions.create.return_value = NS(choices=[NS(message=NS(content=' Hi '))])
        self.assertEqual(OpenAIChat('test-model', client=client).complete([{'role': 'user', 'content': 'x'}]), 'Hi')
        self.assertNotIn('temperature', client.chat.completions.create.call_args.kwargs)
        client.chat.completions.create.return_value = NS(choices=[NS(message=NS(content=None))])
        with self.assertRaises(ValueError):
            OpenAIChat('test-model', client=client).complete([{'role': 'user', 'content': 'x'}])
