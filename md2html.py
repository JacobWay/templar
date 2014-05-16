import re
from random import randint
from hashlib import sha1
import cgi

TAB_SIZE = 4
SALT = bytes(randint(0, 1000000))
def hash_text(s, label):
    return label + '-' + sha1(SALT + s.encode("utf-8")).hexdigest()

def process(text):
    text = handle_whitespace(text)
    text, variables = store_vars(text)
    hashes = {}
    text = hash_codeblocks(text, hashes)
    text = blockquote_re.sub(blockquote_sub, text)
    # links = hash_links(text)
    # text = convert_lists(text, True)
    # text = convert_lists(text, False)
    # text, codes = hash_codes(text)
    # text, tags = hash_tags(text)
    # text = link_re.sub(link_sub, text)
    # text = emphasis_re.sub(emphasis_sub, text)
    # text = atx_header_re.sub(atx_header_sub, text)
    # text = setext_header_re.sub(setext_header_sub, text)
    # text = escape_re.sub(escapes_sub, text)
    # text = paragraph_re.sub(paragraph_sub, text)
    # text = unhash_links(text, links)
    # text = unhash_codes(text, codes)
    # text = unhash_tags(text, tags)
    # text = unhash_codeblocks(text, mappings)
    return text

codeblock_re = re.compile(r"""
    (
        (?:(?<=\n)|(?<=\A))
        [ ]{4}.+?\n
        (?:
            \n
           |
            (?:
                [ ]{4}.+?\n
            )
        )+
        (?=\n*(?![ ]{4}))
    )
""", re.S | re.X)
def hash_codeblocks(text, hashes):
    def codeblock_sub(match):
        block = match.group(1).rstrip('\n')
        block = re.sub(r'(?:(?<=\n)|(?<=\A)) {4}', '', block)
        hashed = hash_text(block, 'pre')
        hashes[hashed] = block
        return hashed + '\n\n'
    return codeblock_re.sub(codeblock_sub, text)

blockquote_re = re.compile(r"""
    (
        (?:(?<=\n)|(?<=\A))
        >.*?\n
        (?:[^\n]+?\n)*
        (?:
            (?:
                >.*?\n
                (?:[^\n]+?\n)*
            )
           |
            \n
        )+
        (?=\n*(?!>))
    )
""", re.S | re.X)
def blockquote_sub(match):
    block = match.group(1).rstrip('\n')
    block = re.sub(r'(?:(?<=\n)|(?<=\A))> ?', '', block)
    return '<blockquote>\n{}\n</blockquote>\n\n'.format(block)

def unhash_codeblocks(text, mappings):
    def retrieve_match(match):
        codeblock = mappings[match.group(1)]
        codeblock = re.sub(r'(?<=\n) {4}', '', codeblock, re.S).lstrip('\n')
        return '\n<pre>{}</pre>\n'.format(codeblock)
    text = re.sub(r'pre-(sha1-[0-9a-f]+)', retrieve_match, text)
    return text

retab_re = re.compile(r'(.*?)\t', re.M)
def retab_sub(match):
    before = match.group(1)
    return before + (' ' * (TAB_SIZE - len(before) % TAB_SIZE))
whitespace_re = re.compile(r'^\s+$', re.M)
def handle_whitespace(text):
    text = retab_re.sub(retab_sub, text)
    text = whitespace_re.sub('', text)
    return text

vars_re = re.compile('^~\s*(.*?):\s*(.*)$', re.M)
def store_vars(text):
    """Extracts variables that can be used in templating engines.

    Each variable is defined on a single line in the following way:

        ~ var: text

    The ~ must be at the start of a newline. var can be any sequence of
    characters that does not contain a ":". Likewise, text can be any
    sequence of characters.

    RETURNS:
    dict; variable to value mappings
    """
    variables = {var: value for var, value in vars_re.findall(text)}
    text = vars_re.sub('', text)
    return text, variables

tag_re = re.compile(r'<[\w\s:/]+?>', re.S)
def hash_tags(text):
    tags = {}
    for tag in tag_re.findall(text):
        tags[hash_text(tag)] = tag
    text = tag_re.sub(lambda m: 'tag-' + hash_text(m.group(0)), text)
    return text, tags

def unhash_tags(text, tags):
    def retrieve_match(match):
        return tags[match.group(1)]
    text = re.sub(r'tag-(sha1-[0-9a-f]+)', retrieve_match, text)
    return text

paragraph_re = re.compile(r"""
    (?<=\n\n)
    (?!<(?:ul|ol|li|pre|h\d)>)
    (.+?)
    (?=\n{2,})
""", re.S | re.X)
def paragraph_sub(match):
    return '<p>{}</p>'.format(match.group(1))

ulist_re = re.compile(r"""
(
    (?<=\n)
    (?:
        (?P<space>[ \t]*)
        (?P<marker>[*+-])
        (?!\ (?P=marker)\ )
        [\t ]+
        (?:.+?)
        (?:
            \Z
           |
            \n
            (?=
                [ \t]*[*+-][ \t]+
            )
            (?!
                (?P=space)[ \t]+[*+-][ \t]+
            )
           |
            \n\n+
            (?=\S)
        )
    )+
)
""", re.S | re.X)

olist_re = re.compile(r"""
(
    (?<=\n)
    (?:
        (?P<space>[ \t]*)
        \d+\.
        [\t ]+
        (?:.+?)
        (?:
            \Z
           |
            \n
            (?=
                [ \t]*\d+\.[ \t]+
            )
            (?!
                (?P=space)[ \t]+\d+\.[ \t]+
            )
           |
            \n\n+
            (?=\S)
        )
    )+
)
""", re.S | re.X)

def convert_lists(text, is_ulist):
    pos = 0
    list_re = ulist_re if is_ulist else olist_re
    tag = 'ul' if is_ulist else 'ol'
    marker = '[+*-]' if is_ulist else '\d+\.'
    while True:
        match = list_re.search(text, pos)
        if not match:
            break
        first_list = match.group(1)
        start = len(re.match(r'[ \t]*', first_list).group(0))
        whole_list = re.split(r'\n(?= {%d}%s )' % (start, marker),
                              '\n' + first_list)[1:]
        items = []
        def truncate(match):
            space = len(match.group(1))
            if space % 4 == 0:
                return ' '*(space - 4)
            return ' '*(space - space%4)

        for item in whole_list:
            item = re.sub(marker, lambda m: ' '*len(m.group(0)), item, 1)
            item = convert_lists(item, is_ulist)
            item = re.sub(r'(?:(?<=\n)|\A)( *)', truncate, item)
            items.append(
                    ' '*start + '<li>\n' +
                    item + \
                    '\n' + ' '*start + '</li>\n')
        list_str = (' '*start) + '<{}>\n'.format(tag) + \
                   '\n'.join(items) + \
                   ' '*start + '</{}>\n'.format(tag)
        start = text.index(first_list)
        end = start + len(first_list)
        text = text[:start] + list_str + text[end:]
        pos = end
    return text



link_re = re.compile(r'(?<!\\)(!?)\[(.*?)\]\((.*?)\)', re.S)
def link_sub(match):
    """Substitutes an <a> tag or an <img> tag.

    The matching for links should be done only
    after a dictionary of link hashes to actual links has been created,
    because this function will substitute the hash of a link instead
    of the link itself. This is so emphasis substitution of underscores
    does not destroy links.
    """
    is_img = match.group(1) != ''
    content = match.group(2)
    link = 'link-' + hash_text(match.group(3))
    if is_img:
        return '<img src="{0}" alt="{1}">'.format(link, content)
    return '<a href="{0}">{1}</a>'.format(link, content)

def hash_links(text):
    """Creates a mapping of link hashes to the links themselves.

    RETURNS:
    dict; mapping of link hashes to links
    """
    links = {}
    for _, _, link in link_re.findall(text):
        links[hash_text(link)] = link
    return links

def unhash_links(text, links):
    """Reverts link hashes in text back to the links themselves."""
    def retrieve_link(match):
        return links[match.group(1)]
    text = re.sub(r'link-(sha1-[0-9a-f]+)', retrieve_link, text)
    return text

code_re = re.compile(r'(?<!\\)(?P<ticks>`+) ?(.*?) ?(?P=ticks)', re.S)
def hash_codes(text):
    codes = {}
    print(code_re.findall(text)[0])
    for _, code in code_re.findall(text):
        codes[hash_text(code)] = code
    text = code_re.sub(lambda m: 'code-' + hash_text(m.group(2)), text)
    return text, codes

def unhash_codes(text, codes):
    def retrieve_match(match):
        code = codes[match.group(1)]
        return '<code>{0}</code>'.format(cgi.escape(code))
    text = re.sub(r'code-(sha1-[0-9a-f]+)', retrieve_match, text)
    return text

emphasis_markers = r'\*{1,3}|_{1,3}'
emphasis_re = re.compile(
        r'(?<!\\)(?P<emph>%s)(?!\s+)(.*?)(?P=emph)' % emphasis_markers,
        re.S)
def emphasis_sub(match):
    """Substitutes <strong>, <em>, and <strong><em> tags."""
    level = len(match.group(1))
    content = match.group(2)
    if level == 3:
        return '<strong><em>{0}</em></strong>'.format(content)
    elif level == 2:
        return '<strong>{0}</strong>'.format(content)
    elif level == 1:
        return '<em>{0}</em>'.format(content)

atx_header_re = re.compile(r'^(#{1,6})\s*(.*)$', re.M)
def atx_header_sub(match):
    """Substitutes atx headers (headers defined using #'s)."""
    level = len(match.group(1))
    title = match.group(2)
    return '<h{0}>{1}</h{0}>'.format(level, title)

setext_header_re = re.compile(r'(?<=\n)(.*?)\n(=+|-+)')
def setext_header_sub(match):
    """Substitutes setext headers (defined with underscores)."""
    title = match.group(1)
    level = 1 if '=' in match.group(2) else 2
    return '<h{0}>{1}</h{0}>'.format(level, title)

escape_re = re.compile(r"""\\(
    \*  |
    `   |
    _   |
    \{  |
    \}  |
    \[  |
    \]  |
    \(  |
    \)  |
    #   |
    \+  |
    -   |
    \.  |
    !
)""", re.X)
def escapes_sub(match):
    return match.group(1)


if __name__ == '__main__':
    import sys
    with open(sys.argv[1], 'r') as f:
        print(process(f.read()))
