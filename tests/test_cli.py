"""Driver loop behaviour with stub chains; no API calls."""
from types import SimpleNamespace as NS
import unittest
from rag.cli import repl
from shared.contracts import Chunk, SearchHit


class StubChain:
    def __init__(self):
        self.asked = []

    def ask(self, question, session_id):
        self.asked.append((question, session_id))
        hit = SearchHit(Chunk('abcdef1234567890', 'some\ncontext', 'lab.pdf', 2), 0.5)
        return NS(answer='Answer text', standalone_question=question, hits=[hit])


def run(lines, chain):
    inputs, output = iter(lines), []

    def read(prompt):
        try:
            return next(inputs)
        except StopIteration:
            raise EOFError
    repl(chain, 's', read=read, write=output.append)
    return output


class CliTests(unittest.TestCase):
    def test_exit_stops_loop_and_blank_lines_are_skipped(self):
        chain = StubChain()
        output = run(['first?', '', 'exit', 'never asked'], chain)
        self.assertEqual(chain.asked, [('first?', 's')])
        self.assertIn('\nAnswer: Answer text\n\nRetrieved context:', output)
        self.assertIn('  [1] score 0.500 · lab.pdf p.2 · abcdef123456', output)
        self.assertIn('      some context', output)

    def test_errors_keep_loop_running_until_eof(self):
        class FailingChain:
            def ask(self, question, session_id):
                raise RuntimeError('boom')
        output = run(['q1', 'q2'], FailingChain())
        self.assertEqual(output.count('Error (RuntimeError): boom'), 2)
