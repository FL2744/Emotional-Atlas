"""Conservative local sentence boundaries for prose, Arabic and Chinese punctuation.

This is punctuation-based segmentation, not a language model. Ambiguous abbreviations,
poetry and punctuation-free speech can require manual line breaks.
"""
import re

ABBREVIATIONS={'mr','mrs','ms','dr','prof','sr','jr','st','vs','etc','e.g','i.e','fig','no','vol','inc','ltd','a.m','p.m'}
CLOSERS='\"\'”’»）)]}'


def split_sentences(text):
    paragraphs=re.split(r'\n[ \t]*\n+',text.replace('\r\n','\n').replace('\r','\n').strip())
    result=[]
    for paragraph in paragraphs:
        p=re.sub(r'[ \t]*\n[ \t]*',' ',paragraph).strip()
        start=0;i=0
        while i<len(p):
            ch=p[i]
            if ch not in '.!?؟。！？':i+=1;continue
            end=i+1
            while end<len(p) and p[end] in '.!?؟。！？':end+=1
            closing=end
            while closing<len(p) and p[closing] in CLOSERS:closing+=1
            if ch=='.':
                # Periods within decimals, addresses and abbreviations are not boundaries.
                if closing<len(p) and not p[closing].isspace():i=end;continue
                token=re.search(r'([\w.]+)\.$',p[:end])
                word=token.group(1) if token else ''
                if closing<len(p) and (word.casefold() in ABBREVIATIONS or re.fullmatch(r'(?:[A-Za-z]\.)*[A-Za-z]',word)):
                    i=end;continue
            # Chinese punctuation does not require a following space.
            segment=p[start:closing].strip()
            if segment:result.append(segment)
            start=closing;i=closing
        tail=p[start:].strip()
        if tail:result.append(tail)
    return result
