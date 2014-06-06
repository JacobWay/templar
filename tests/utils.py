import sys
sys.path.insert(0, '..')

import os
import unittest
import re
from markdown import convert, Markdown


class TemplarTest(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    @staticmethod
    def openData(filename):
        path = os.path.join(os.path.dirname(__file__), 'test-data')
        if not os.path.exists(os.path.join(path, filename)):
            print('No file', filename, 'found in', path)
        with open(os.path.join(path, filename), 'r') as f:
            return f.read()

    def stripLeadingWhitespace(self, text):
        text = text.strip('\n')
        length = len(re.match('\s*', text).group(0))
        return '\n'.join(line[length:]
                         for line in text.split('\n')
                         if line.strip())

    def ignoreWhitespace(self, text):
        text = self.stripLeadingWhitespace(text)
        return re.sub('\s+', '', text, flags=re.S)

    def assertMarkdown(self, markdown, output):
        markdown = self.stripLeadingWhitespace(markdown)
        output = self.stripLeadingWhitespace(output)
        try:
            self.assertEqual(output, convert(markdown))
        except AssertionError:
            raise

    def assertMarkdownIgnoreWS(self, markdown, output):
        markdown = self.stripLeadingWhitespace(markdown)
        try:
            self.assertEqual(self.ignoreWhitespace(output),
                             self.ignoreWhitespace(convert(markdown)))
        except AssertionError:
            raise

def main():
    unittest.main()