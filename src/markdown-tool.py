import re

class Token:
    """
    A class representing a single token.
    """

    def __init__(self, token_type, value, line, column):
        self.token_type = token_type
        self.value = value
        self.line = line
        self.column = column

    def __repr__(self):
        return f'Token({self.token_type}, {repr(self.value)}, line={self.line}, column={self.column})'


class MarkdownLexer:
    """
    Lexer for tokenizing markdown content.
    """

    def __init__(self, file_content):
        self.text = file_content
        self.position = 0
        self.line = 1
        self.column = 1
        self.tokens = []
        self._tokenize()

    def _tokenize(self):
        """
        Tokenize the entire file content based on markdown grammar.
        """
        while self.position < len(self.text):
            current_char = self.text[self.position]

            if current_char == '\\':
                self._handle_escape_sequence()
            elif current_char == '#':
                self._lex_heading()
            elif current_char == '*':
                self._handle_asterisk()
            elif current_char == '+':
                self._handle_plus()
            elif current_char == '-':
                self._handle_dash()
            elif current_char == '_':
                self._handle_underscore()
            elif current_char.isdigit():
                self._handle_digit()
            elif current_char == '>':
                self._lex_blockquote()
            elif current_char == '`':
                self._lex_code_block()
            elif current_char == '|':
                self._lex_table()
            elif current_char == '<':
                self._lex_html_block()
            elif current_char == '[':
                self._handle_bracket()
            elif current_char == '~':
                self._lex_strikethrough()
            elif current_char == '\n':
                self._advance_line()
            else:
                self._lex_paragraph_or_text()

        self.tokens.append(Token('EOF', None, self.line, self.column))

    # New functions to handle specific characters

    def _handle_escape_sequence(self):
        """
        Handle escape sequences in the Markdown text.
        If a backslash is followed by a special character, treat it as a literal character.
        """
        start_line = self.line
        start_column = self.column

        # Ensure there is another character after the backslash
        if self.position + 1 < len(self.text):
            # Generate a TEXT token for the escaped character
            escaped_char = self.text[self.position + 1]
            self.tokens.append(Token('TEXT', escaped_char, start_line, start_column))

            # Advance past the backslash and the escaped character
            self.position += 2
            self.column += 2
        else:
            # If backslash is at the end of the text, treat it as a literal backslash
            self.tokens.append(Token('TEXT', '\\', start_line, start_column))
            self._advance()

    def _handle_asterisk(self):
        """ Handle '*' character: can be horizontal rule, unordered list, or emphasis/strong. """
        if self._is_horizontal_rule():
            self._lex_horizontal_rule()
        elif self._peek_next_char(1) == ' ':
            self._lex_unordered_list_item()
        else:
            self._lex_emphasis_or_strong()

    def _handle_plus(self):
        """ Handle '+' character: can be unordered list or normal text. """
        if self._peek_next_char(1) == ' ':
            self._lex_unordered_list_item()
        else:
            self._lex_paragraph_or_text()  # Assume it's text if not a list item

    def _handle_dash(self):
        """ Handle '-' character: can be horizontal rule, unordered list, or normal text. """
        if self._is_horizontal_rule():
            self._lex_horizontal_rule()
        elif self._peek_next_char(1) == ' ':
            self._lex_unordered_list_item()
        else:
            self._lex_paragraph_or_text()  # Assume it's text if not a list item

    def _handle_underscore(self):
        """ Handle '_' character: can be horizontal rule or emphasis/strong. """
        if self._is_horizontal_rule():
            self._lex_horizontal_rule()
        else:
            self._lex_emphasis_or_strong()

    def _handle_bracket(self):
        """ Handle '[' character: can be a link, image, or footnote. """
        if self._peek_next_char(1) == '^':
            self._lex_footnote()
        else:
            self._lex_link_or_image()

    def _handle_digit(self):
        """ Handle digit character: can be part of an ordered list item. """
        if self._peek_next_char(1) == '.':
            self._lex_ordered_list_item()
        else:
            self._lex_paragraph_or_text()  # Assume it's text if not part of an ordered list

    # Existing methods

    def _lex_heading(self):
        """
        Tokenize a heading. If the heading is not correctly formed, generate an error token.
        """
        start_line = self.line
        start_column = self.column

        level = 0
        while self._peek_next_char() == '#':
            self._advance()
            level += 1

        if level > 6:
            self.tokens.append(Token('ERROR', 'Invalid heading level (too many #)', start_line, start_column))
            return

        if self._peek_next_char() != ' ':
            self.tokens.append(Token('ERROR', 'Expected space after heading #', start_line, start_column))
            return

        self._advance()  # skip space
        value = self._read_until('\n')
        self.tokens.append(Token(f'HEADING_{level}', value.strip(), start_line, start_column))

    def _lex_unordered_list_item(self):
        """
        Tokenize an unordered list item. If the list item is not correctly formed, generate an error token.
        """
        start_line = self.line
        start_column = self.column

        marker = self._advance()  # * or - or +
        if self._peek_next_char() != ' ':
            self.tokens.append(Token('ERROR', f'Expected space after list marker "{marker}"', start_line, start_column))
            return

        self._advance()  # skip space
        value = self._read_until('\n')
        self.tokens.append(Token('UNORDERED_LIST_ITEM', value.strip(), start_line, start_column))

    def _lex_ordered_list_item(self):
        """
        Tokenize an ordered list item. If the list item is not correctly formed, generate an error token.
        """
        start_line = self.line
        start_column = self.column

        number = self._read_digits()
        if self._peek_next_char() != '.':
            self.tokens.append(Token('ERROR', 'Expected "." after ordered list number', start_line, start_column))
            return

        self._advance()  # skip dot
        if self._peek_next_char() != ' ':
            self.tokens.append(Token('ERROR', 'Expected space after "." in ordered list item', start_line, start_column))
            return

        self._advance()  # skip space
        value = self._read_until('\n')
        self.tokens.append(Token('ORDERED_LIST_ITEM', value.strip(), start_line, start_column))

    def _lex_blockquote(self):
        """
        Tokenize a blockquote. If the blockquote is not correctly formed, generate an error token.
        """
        start_line = self.line
        start_column = self.column

        self._advance()  # skip >
        if self._peek_next_char() != ' ':
            self.tokens.append(Token('ERROR', 'Expected space after ">" in blockquote', start_line, start_column))
            return

        self._advance()  # skip space
        value = self._read_until('\n')
        self.tokens.append(Token('BLOCKQUOTE', value.strip(), start_line, start_column))

    def _lex_code_block(self):
        """
        Tokenize a code block. If the code block is not correctly closed, generate an error token.
        """
        start_line = self.line
        start_column = self.column

        self._advance()  # skip the first backtick

        # Capture the language type if it exists
        language = ''
        if self.text[self.position:self.position+2] == '``':
            self.position += 2  # skip the next two backticks
            self.column += 2

        # Check if there's a language specified right after the backticks
        if not self.text[self.position:self.position+1].isspace() and self.text[self.position:self.position+1] != '\n':
            language_start = self.position
            while self.position < len(self.text) and self.text[self.position] not in ['\n', ' ']:
                self._advance()
            language = self.text[language_start:self.position].strip()

        self._advance()  # skip newline after language or backticks
        value = self._read_until('```')

        if not self.text[self.position:self.position+3] == '```':
            self.tokens.append(Token('ERROR', 'Unclosed code block', start_line, start_column))
            return

        self.tokens.append(Token('CODE_BLOCK', {'language': language, 'content': value.strip()}, start_line, start_column))
        self._advance()  # skip the closing ```
        self._advance()
        self._advance()

    def _lex_horizontal_rule(self):
        """
        Tokenize a horizontal rule. Ensure no extra characters are present on the line after the rule.
        """
        start_line = self.line
        start_column = self.column

        # Check if we have a valid horizontal rule pattern (e.g., "---", "***", "___")
        if self.text[self.position:self.position+3] not in ['---', '***', '___']:
            self.tokens.append(Token('ERROR', 'Invalid horizontal rule', start_line, start_column))
            return

        # Advance past the horizontal rule characters
        self.position += 3
        self.column += 3

        # Check if the rest of the line contains only whitespace or a newline
        rest_of_line = self._read_until('\n').strip()
        if rest_of_line:
            self.tokens.append(Token('ERROR', 'Invalid characters after horizontal rule', start_line, start_column))
            return

        self.tokens.append(Token('HORIZONTAL_RULE', self.text[start_column-1:self.position], start_line, start_column))

    def _is_horizontal_rule(self):
        """
        Check if the current line represents a horizontal rule.
        """
        start_pos = self.position
        line_content = self._read_until('\n').strip()
        self.position = start_pos  # Reset position to original

        # Horizontal rules are typically 3 or more '-', '*', or '_' characters
        if len(line_content) >= 3 and all(c in ['-', '*', '_'] for c in line_content):
            return True
        return False

    def _lex_table(self):
        """
        Tokenize a table.
        """
        start_line = self.line
        start_column = self.column

        header = self._read_until('\n')
        divider = self._read_until('\n')
        self.tokens.append(Token('TABLE_HEADER', header.strip(), start_line, start_column))
        self.tokens.append(Token('TABLE_DIVIDER', divider.strip(), self.line, self.column))

        while self._peek_next_char() == '|':
            start_line = self.line
            start_column = self.column
            row = self._read_until('\n')
            self.tokens.append(Token('TABLE_ROW', row.strip(), start_line, start_column))

    def _lex_html_block(self):
        """
        Tokenize an HTML block.
        """
        start_line = self.line
        start_column = self.column

        value = self._read_until('>')
        self.tokens.append(Token('HTML_BLOCK', value.strip(), start_line, start_column))
        self._advance()  # skip '>'

    def _lex_footnote(self):
        """
        Tokenize a footnote. If the footnote is not correctly formed, generate an error token.
        """
        start_line = self.line
        start_column = self.column

        # Check if it's a valid footnote start
        if self._peek_next_char() != '[' or self._peek_next_char(1) != '^':
            self.tokens.append(Token('ERROR', 'Expected footnote format [^digit]:', start_line, start_column))
            return

        self._advance()  # skip '['
        self._advance()  # skip '^'
        digit = self._read_digits()

        # Validate footnote digit and closing bracket
        if not digit or self._peek_next_char() != ']':
            self.tokens.append(Token('ERROR', 'Malformed footnote syntax', start_line, start_column))
            return

        self._advance()  # skip ']'

        # Validate colon after the footnote digit
        if self._peek_next_char() != ':':
            self.tokens.append(Token('ERROR', 'Expected ":" after footnote number', start_line, start_column))
            return

        self._advance()  # skip ':'
        value = self._read_until('\n')
        self.tokens.append(Token('FOOTNOTE', f'{digit}: {value.strip()}', start_line, start_column))

    def _lex_link_or_image(self):
        """
        Tokenize a link or an image. If the link or image is not correctly formed, generate an error token.
        """
        start_line = self.line
        start_column = self.column

        is_image = False
        if self._peek_next_char() == '!':
            self._advance()  # skip '!'
            is_image = True

        # Validate the opening bracket
        if self._peek_next_char() != '[':
            self.tokens.append(Token('ERROR', 'Expected "[" to start link/image text', start_line, start_column))
            return

        self._advance()  # skip '['
        alt_text = self._read_until(']')

        # Validate the closing bracket for alt text
        if self._peek_next_char() != ']':
            self.tokens.append(Token('ERROR', 'Expected closing "]" for link/image text', start_line, start_column))
            return

        self._advance()  # skip ']'

        # Validate the opening parenthesis for URL
        if self._peek_next_char() != '(':
            self.tokens.append(Token('ERROR', 'Expected "(" to start link/image URL', start_line, start_column))
            return

        self._advance()  # skip '('
        url = self._read_until(')')

        # Validate the closing parenthesis for URL
        if self._peek_next_char() != ')':
            self.tokens.append(Token('ERROR', 'Expected closing ")" for link/image URL', start_line, start_column))
            return

        self._advance()  # skip ')'

        if is_image:
            self.tokens.append(Token('IMAGE', {'alt_text': alt_text, 'url': url}, start_line, start_column))
        else:
            self.tokens.append(Token('LINK', {'text': alt_text, 'url': url}, start_line, start_column))

    def _lex_emphasis_or_strong(self):
        """
        Tokenize emphasis or strong emphasis text.
        Check for matching closing markers on the same line. If there's no matching marker,
        or a newline is encountered first, treat the content as plain text.
        """
        start_line = self.line
        start_column = self.column

        marker = self._peek_next_char()

        # Check if it's a strong emphasis (e.g., '**' or '__')
        if self.text[self.position:self.position+2] in ['**', '__']:
            marker = self.text[self.position:self.position + 2]
            self.position += 2  # Skip '**' or '__'
            self.column += 2

            end_pos = self.position
            while end_pos < len(self.text) and self.text[end_pos:end_pos+2] != marker and self.text[end_pos] != '\n':
                end_pos += 1

            if end_pos >= len(self.text) or self.text[end_pos] == '\n':
                # No closing marker found on the same line, treat it as plain text
                self.tokens.append(Token('TEXT', marker + self.text[self.position:end_pos], start_line, start_column))
                self.position = end_pos  # Move to the newline or end of the text
                self.column += end_pos - self.position
                return

            # Closing '**' or '__' found on the same line
            value = self.text[self.position:end_pos]
            self.tokens.append(Token('STRONG', value.strip(), start_line, start_column))
            self.position = end_pos + 2  # Move past the closing '**' or '__'
            self.column += len(value) + 2

        # Check if it's an emphasis (e.g., '*' or '_')
        elif marker in ['*', '_']:
            self._advance()  # Skip '*' or '_'
            end_pos = self.position
            while end_pos < len(self.text) and self.text[end_pos] != marker and self.text[end_pos] != '\n':
                end_pos += 1

            if end_pos >= len(self.text) or self.text[end_pos] == '\n':
                # No closing marker found on the same line, treat it as plain text
                self.tokens.append(Token('TEXT', marker + self.text[self.position:end_pos], start_line, start_column))
                self.position = end_pos  # Move to the newline or end of the text
                self.column += end_pos - self.position
                return

            # Closing '*' or '_' found on the same line
            value = self.text[self.position:end_pos]
            self.tokens.append(Token('EMPHASIS', value.strip(), start_line, start_column))
            self.position = end_pos + 1  # Move past the closing '*' or '_'
            self.column += len(value) + 1

        else:
            # Not a valid emphasis or strong, treat it as plain text
            self.tokens.append(Token('TEXT', marker, start_line, start_column))
            self._advance()

    def _lex_strikethrough(self):
        """
        Tokenize strikethrough text.
        Check for exactly two '~' characters at the start and for a matching closing marker
        on the same line. If there are more than two '~' characters or no closing marker is found,
        treat it as plain text.
        """
        start_line = self.line
        start_column = self.column

        # Check if it's a strikethrough (e.g., '~~')
        if self.text[self.position:self.position+2] == '~~' and self.text[self.position+2] != '~':
            self.position += 2  # Skip the opening '~~'
            self.column += 2

            end_pos = self.position
            while end_pos < len(self.text) and self.text[end_pos:end_pos+2] != '~~' and self.text[end_pos] != '\n':
                end_pos += 1

            if end_pos >= len(self.text) or self.text[end_pos] == '\n':
                # No closing marker found on the same line, treat it as plain text
                self.tokens.append(Token('TEXT', '~~' + self.text[self.position:end_pos], start_line, start_column))
                self.position = end_pos  # Move to the newline or end of the text
                self.column += end_pos - self.position
                return

            # Closing '~~' found on the same line
            value = self.text[self.position:end_pos]
            self.tokens.append(Token('STRIKETHROUGH', value.strip(), start_line, start_column))
            self.position = end_pos + 2  # Move past the closing '~~'
            self.column += len(value) + 2

        else:
            # If it's not exactly two '~' or more than two '~', treat it as plain text
            self.tokens.append(Token('TEXT', self._advance(), start_line, start_column))

    def _lex_paragraph_or_text(self):
        """
        Tokenize a paragraph or inline text.
        """
        start_line = self.line
        start_column = self.column

        value = self._read_until('\n\n')
        if value:
            self.tokens.append(Token('PARAGRAPH', value.strip(), start_line, start_column))

    def _read_until(self, stop_char):
        """
        Read characters until a stop character or string is found.
        """
        start = self.position
        while not self.text[self.position:].startswith(stop_char) and self.position < len(self.text):
            self._advance()
        return self.text[start:self.position]

    def _read_digits(self):
        """
        Read consecutive digits.
        """
        start = self.position
        while self._peek_next_char().isdigit():
            self._advance()
        return self.text[start:self.position]

    def _peek_next_char(self, offset=0):
        """
        Peek at the next character without advancing the position.
        """
        if self.position + offset < len(self.text):
            return self.text[self.position + offset]
        return ''

    def _advance(self):
        """
        Advance the position by one character.
        """
        char = self.text[self.position]
        self.position += 1
        if char == '\n':
            self.line += 1
            self.column = 1
        else:
            self.column += 1
        return char

    def _advance_line(self):
        """
        Advance to the next line.
        """
        self.position += 1
        self.line += 1
        self.column = 1

    def get_next_token(self):
        """
        Return the next token from the tokens list.
        """
        if self.tokens:
            return self.tokens.pop(0)
        return Token('EOF', None, self.line, self.column)


if __name__ == '__main__':
    import sys

    if len(sys.argv) != 2:
        print("Usage: python markdown_lexer.py <filename>")
        sys.exit(1)

    filename = sys.argv[1]

    # Specify the encoding for the file
    with open(filename, 'r', encoding='utf-8') as file:
        content = file.read()

    lexer = MarkdownLexer(content)

    while True:
        token = lexer.get_next_token()
        print(token)
        if token.token_type == 'EOF':
            break
