import io
import json
import threading
import unittest
from unittest.mock import patch
import idioms
from analysis import AnalysisError, Cancelled

class IdiomTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records=idioms.dictionaries()
        cls.goat=next(r for r in cls.records if r['phrase']=='get your goat')

    def match(self,**kw):
        return dict(idiom_id=self.goat['id'],kind='imagery',quote='stole my goat',
                    explanation='The taking of the goat echoes the expression.',
                    alternative='It may simply depict an animal theft.',**kw)

    def test_dictionary_languages_and_grounding(self):
        self.assertTrue({'en','ar','zh'} <= {r['language'] for r in self.records})
        found=idioms.shortlist('A stranger stole my goat.',['get your goat'],self.records)
        self.assertIn(self.goat,found)
        self.assertFalse(idioms.shortlist('A goat grazed peacefully.',[],self.records))
        self.assertTrue(idioms.shortlist('他守株待兔。',[],self.records))

    def test_reject_hallucinated_quote_and_dictionary_id(self):
        for key,value in [('quote','I was furious'),('idiom_id','invented')]:
            m=self.match();m[key]=value
            with self.assertRaises(AnalysisError):idioms.validate_matches({'matches':[m]},'Someone stole my goat.',[self.goat])

    def test_session_roundtrip_and_old_session(self):
        matches=idioms.validate_matches({'matches':[self.match()]},'Someone stole my goat.',[self.goat])
        data={'version':'1','paragraphs':{'1':{'matches':matches,'provider':'openai','model':idioms.connection()[1]}}}
        restored=idioms.restore(json.loads(json.dumps(data)),['Someone stole my goat.'])
        self.assertEqual(restored[1]['matches'],matches)
        self.assertEqual(idioms.restore(None,['old']),{})
        with self.assertRaises(AnalysisError):idioms.restore(data,['Different text'])

    def test_scan_goat_echo_and_literal_negative(self):
        for matches in ([self.match()],[]):
            with patch('idioms.request_json',side_effect=[({'phrases':['get your goat']},{'input_tokens':1,'output_tokens':2}),({'matches':matches},{'input_tokens':3,'output_tokens':4})]):
                rows,usage=idioms.scan('Someone stole my goat.',self.records,'key',threading.Event())
                self.assertEqual(len(rows),len(matches))
                self.assertEqual(usage,{'input_tokens':4,'output_tokens':6})

    def test_protocols_and_cancellation(self):
        for provider in ('openai','arc'):
            def opener(req,timeout):
                body=json.loads(req.data)
                self.assertNotIn('key',json.dumps(body))
                result=json.dumps({'phrases':[]})
                if provider=='arc':
                    self.assertIn('messages',body)
                    response={'choices':[{'finish_reason':'stop','message':{'content':result}}]}
                else:
                    self.assertFalse(body['store'])
                    response={'status':'completed','output':[{'type':'message','content':[{'type':'output_text','text':result}]}]}
                return io.StringIO(json.dumps(response))
            r,_=idioms.request_json('prompt',{},idioms.PROPOSALS,'key',threading.Event(),provider,None,opener)
            self.assertEqual(r,{'phrases':[]})
        cancel=threading.Event();cancel.set()
        with self.assertRaises(Cancelled):idioms.scan('dream',self.records,'key',cancel)

    def test_cross_language_retrieval(self):
        for phrase in ['بلغ السيل الزبى','杯弓蛇影']:
            self.assertTrue(idioms.shortlist('An English-language dream.',[phrase],self.records))

if __name__=='__main__':unittest.main()
