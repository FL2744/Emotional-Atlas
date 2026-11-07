import copy
import io
import json
import threading
import unittest
import urllib.error
from analysis import *


def example():
    return {'id':1,'intensity':.8,'valence':-.7,'direction':-1,
        'direction_status':'inward','tone':'negative','uncertainty':'low',
        'summary':'The speaker expresses intense self-directed anger.','uncertainty_note':'',
        'emotions':[{'label':'anger','experiencer':'speaker','target':'self',
            'intensity':.8,'valence':-.7,'direction':-1,'explanation':'The anger targets the speaker.',
            'evidence':[{'quote':'furious with myself','signal_words':['furious','myself'],
                'explanation':'Furious signals strength; myself identifies an inward target.'}]}]}


class AnalysisTests(unittest.TestCase):
    def setUp(self):
        self.batch=[{'id':1,'text':'I was furious with myself.','context_before':'','context_after':''}]

    def test_paragraphs_keep_wrapped_lines(self):
        self.assertEqual(split_paragraphs(' One\nwrapped line.\n \nNext.\r\n\r\nThird.'),['One wrapped line.','Next.','Third.'])
        self.assertEqual(split_paragraphs('a\nb','line'),['a','b'])
        self.assertEqual(split_paragraphs('   '),[])

    def test_gutenberg_wrapper(self):
        text='front\n*** START OF THE PROJECT GUTENBERG EBOOK TEST ***\nbody\n*** END OF THE PROJECT GUTENBERG EBOOK TEST ***\nlicense'
        self.assertEqual(gutenberg_body(text),'body')

    def test_resume_keeps_original_ids_and_context(self):
        groups=list(batches(['a','b','c','d'],{1:{}},size=2))
        self.assertEqual([[r['id'] for r in group] for group in groups],[[2,3],[4]])
        self.assertEqual(groups[0][0]['context_before'],'a')

    def test_large_batch_split_without_dropping_paragraph(self):
        paragraphs=['a'*10000,'b'*10000,'c'*10000]
        groups=list(batches(paragraphs,char_budget=18000))
        self.assertEqual([r['text'] for g in groups for r in g],paragraphs)

    def test_reject_wrong_ids_and_hallucinated_evidence(self):
        valid=example()
        self.assertEqual(validate_results({'paragraphs':[valid]},self.batch),[valid])
        for mutation in ('id','quote','signal','score','direction','nan'):
            r=copy.deepcopy(valid)
            if mutation=='id':r['id']=2
            if mutation=='quote':r['emotions'][0]['evidence'][0]['quote']='happy'
            if mutation=='signal':r['emotions'][0]['evidence'][0]['signal_words']=['happy']
            if mutation=='score':r['intensity']=7
            if mutation=='direction':r['direction_status']='outward'
            if mutation=='nan':r['intensity']=float('nan')
            with self.subTest(mutation=mutation),self.assertRaises(AnalysisError):
                validate_results({'paragraphs':[r]},self.batch)

    def test_null_direction_allowed_and_not_equated_with_zero(self):
        r=example();r['direction_status']='unclear';r['direction']=None
        self.assertIsNone(validate_results({'paragraphs':[r]},self.batch)[0]['direction'])

    def test_request_and_completed_response(self):
        captured=[]
        def fake(request,timeout):
            captured.append(json.loads(request.data))
            return io.StringIO(json.dumps({'status':'completed','output':[{'type':'message','content':[{'type':'output_text','text':json.dumps({'paragraphs':[example()]})}]}],'usage':{'input_tokens':100}}))
        results,usage=analyze_batch(self.batch,'test-secret',threading.Event(),opener=fake)
        self.assertEqual(captured[0]['model'],'gpt-6-luna')
        self.assertFalse(captured[0]['store'])
        self.assertEqual(results[0]['id'],1)
        self.assertEqual(usage['input_tokens'],100)
        self.assertNotIn('test-secret',json.dumps(captured))

    def test_cancel_prevents_request(self):
        event=threading.Event();event.set()
        with self.assertRaises(Cancelled):analyze_batch(self.batch,'test',event,opener=lambda *a,**k:self.fail('sent after cancel'))

    def test_auth_error_is_safe(self):
        def fail(*a,**k):raise urllib.error.HTTPError(ENDPOINT,401,'test-secret',{},None)
        with self.assertRaises(AnalysisError) as context:analyze_batch(self.batch,'test-secret',threading.Event(),opener=fail)
        self.assertNotIn('test-secret',str(context.exception))

    def test_export_resume_and_corruption(self):
        data=export_session([self.batch[0]['text']],{1:example()},'Test',{})
        paragraphs,results=load_session(data)
        self.assertEqual(results[1],example())
        self.assertEqual(paragraphs,[self.batch[0]['text']])
        data['results'].append(example())
        with self.assertRaises(AnalysisError):load_session(data)

class EvidenceRepairTests(unittest.TestCase):
    def test_typography_restores_original_span(self):
        source = 'I felt “terribly  sad”—and couldn’t sleep.'
        self.assertEqual(source_span('"terribly sad"-and couldn\'t sleep', source),
                         '“terribly  sad”—and couldn’t sleep')
        self.assertIsNone(source_span('terribly happy', source))
        self.assertIsNone(source_span('sad and could sleep', source))
        self.assertIsNone(source_span('   ', source))

    def test_words_cannot_be_dropped_or_reordered(self):
        for quote in ['I was happy', 'I was ... happy', 'happy not was I']:
            self.assertIsNone(source_span(quote, 'I was not happy'))

    def test_ambiguous_normalization_is_rejected(self):
        self.assertIsNone(source_span('very   sad', 'very  sad; very sad'))

    def test_validation_restores_signal_words(self):
        result = example()
        result['emotions'][0]['evidence'][0].update(quote='furious with myself', signal_words=['with myself'])
        source = 'I was furious with  myself.'
        validated = validate_results({'paragraphs':[result]}, [{'id':1,'text':source}])[0]
        evidence = validated['emotions'][0]['evidence'][0]
        self.assertEqual(evidence['quote'], 'furious with  myself')
        self.assertEqual(evidence['signal_words'], ['with  myself'])
        session = export_session([source], {1:validated}, 'Test', {})
        self.assertEqual(load_session(session)[1][1], validated)

    def responses(self, results, captured):
        def fake(request, timeout):
            captured.append(json.loads(request.data))
            result = results[min(len(captured)-1, len(results)-1)]
            return io.StringIO(json.dumps({'status':'completed','output':[{'type':'message',
                'content':[{'type':'output_text','text':json.dumps({'paragraphs':[result]})}]}],
                'usage':{'input_tokens':100,'output_tokens':50,'total_tokens':150}}))
        return fake

    def test_invalid_quote_is_retried_with_feedback_and_usage(self):
        bad=example();bad['emotions'][0]['evidence'][0]['quote']='furious at myself'
        captured=[];status=[]
        rows, usage = analyze_batch([{'id':1,'text':'I was furious with myself.'}],
            'test',threading.Event(),status.append,self.responses([bad,example()],captured))
        self.assertEqual(len(captured),2)
        self.assertIn('CORRECTION REQUIRED',captured[1]['instructions'])
        self.assertEqual(usage['input_tokens'],200)
        self.assertEqual(rows[0],example())
        self.assertEqual(len(status),1)

    def test_invalid_quotes_never_accepted_after_retry_limit(self):
        bad=example();bad['emotions'][0]['evidence'][0]['quote']='invented evidence'
        captured=[]
        with self.assertRaisesRegex(AnalysisError,'Automatic correction'):
            analyze_batch([{'id':1,'text':'I was furious with myself.'}], 'test',
                threading.Event(),opener=self.responses([bad],captured))
        self.assertEqual(len(captured),3)

    def test_stop_prevents_correction_request(self):
        bad=example();bad['emotions'][0]['evidence'][0]['quote']='invented evidence'
        captured=[];cancel=threading.Event()
        with self.assertRaises(Cancelled):
            analyze_batch([{'id':1,'text':'I was furious with myself.'}], 'test',cancel,
                lambda _:cancel.set(),self.responses([bad],captured))
        self.assertEqual(len(captured),1)

class ResilientAnalysisTests(unittest.TestCase):
    def setUp(self):
        self.batch=[{'id':1,'text':'I was furious with myself.'},
                    {'id':2,'text':'I was furious with myself.'}]
        self.good=example()
        self.bad=example();self.bad['id']=2
        self.bad['emotions'][0]['evidence'][0]['quote']='invented wording'
        self.indexed=example();self.indexed['id']=2
        self.indexed['emotions'][0]['evidence']=[{'word_ids':[2,4],'explanation':'Anger is directed at self.'}]

    def fake(self, outputs, calls):
        def send(request,timeout):
            calls.append(json.loads(request.data))
            return io.StringIO(json.dumps({'status':'completed','output':[{'type':'message',
                'content':[{'type':'output_text','text':json.dumps({'paragraphs':outputs[len(calls)-1]})}]}],
                'usage':{'input_tokens':10,'output_tokens':20}}))
        return send

    def test_retains_valid_neighbor_before_individual_repair(self):
        calls=[]
        iterator=analyze_resilient_batch(self.batch,'test',threading.Event(),
            opener=self.fake([[self.good,self.bad],[self.indexed]],calls))
        first=next(iterator)
        self.assertEqual(first[1][0][0]['id'],1)
        self.assertEqual(len(calls),1)
        second=next(iterator)
        evidence=second[1][0][0]['emotions'][0]['evidence'][0]
        self.assertEqual(evidence['quote'],'furious with myself')
        self.assertEqual(evidence['signal_words'],['furious','myself'])
        payload=json.loads(calls[1]['input'])['paragraphs']
        self.assertEqual([p['id'] for p in payload],[2])
        self.assertIn('source_words',payload[0])
        self.assertEqual(list(iterator),[])

    def test_unresolved_result_flagged_without_scores(self):
        self.indexed['emotions'][0]['evidence'][0]['word_ids']=[999]
        calls=[]
        events=list(analyze_resilient_batch(self.batch,'test',threading.Event(),
            opener=self.fake([[self.good,self.bad],[self.indexed]],calls)))
        self.assertEqual([e[0] for e in events],['result','result','review'])
        self.assertEqual(events[-1][1][0],2)
        self.assertEqual(events[1][1][0],[])
        self.assertEqual(sum(e[1][1]['input_tokens'] for e in events if e[0]=='result'),20)
        data=export_session([p['text'] for p in self.batch],{1:self.good},'Test',{},
                            {2:events[-1][1][1]})
        self.assertIn('2',data['reviews'])
        self.assertEqual(list(load_session(data)[1]),[1])

    def test_cancel_after_retaining_success_stops_repair(self):
        calls=[];cancel=threading.Event()
        iterator=analyze_resilient_batch(self.batch,'test',cancel,
            opener=self.fake([[self.good,self.bad]],calls))
        next(iterator);cancel.set()
        with self.assertRaises(Cancelled):next(iterator)
        self.assertEqual(len(calls),1)

    def test_transport_error_still_stops_instead_of_flagging_every_paragraph(self):
        def fail(*args,**kwargs):raise urllib.error.HTTPError(ENDPOINT,401,'Unauthorized',{},None)
        with self.assertRaisesRegex(AnalysisError,'API key'):
            list(analyze_resilient_batch(self.batch,'test',threading.Event(),opener=fail))

class ArcTests(unittest.TestCase):
    def setUp(self):
        self.batch=[{'id':1,'text':'I was furious with myself.','context_before':'','context_after':''}]
    def response(self, row, finish='stop'):
        return io.StringIO(json.dumps({'choices':[{'finish_reason':finish,
            'message':{'content':json.dumps({'paragraphs':[row]})}}],
            'usage':{'prompt_tokens':12,'completion_tokens':34,'total_tokens':46}}))

    def test_arc_request_and_usage(self):
        def send(request,timeout):
            self.assertEqual(request.full_url,ARC_ENDPOINT)
            self.assertEqual(request.get_header('Authorization'),'Bearer arc-secret')
            body=json.loads(request.data)
            self.assertEqual(body['model'],ARC_MODEL)
            self.assertNotIn('instructions',body)
            self.assertNotIn('reasoning',body)
            self.assertEqual(body['response_format'],{'type':'json_object'})
            self.assertIn('schema',body['messages'][0]['content'])
            self.assertNotIn('arc-secret',request.data.decode())
            return self.response(example())
        rows,usage=analyze_batch(self.batch,'arc-secret',threading.Event(),opener=send,provider='arc')
        self.assertEqual(rows[0]['id'],1)
        self.assertEqual(usage,{'input_tokens':12,'output_tokens':34,'total_tokens':46})

    def test_arc_repair_uses_same_provider_and_model(self):
        calls=[]
        def send(request,timeout):
            self.assertEqual(request.full_url,ARC_ENDPOINT)
            body=json.loads(request.data);calls.append(body)
            self.assertEqual(body['model'],'custom-arc-model')
            row=example()
            if len(calls)==1:
                row['emotions'][0]['evidence'][0]['quote']='invented quote'
            else:
                self.assertIn('source_words',body['messages'][1]['content'])
                row['emotions'][0]['evidence']=[{'word_ids':[2,4], 'explanation':'Exact words.'}]
            return self.response(row)
        events=list(analyze_resilient_batch(self.batch,'arc-secret',threading.Event(),
            opener=send,provider='arc',model='custom-arc-model'))
        self.assertEqual(len(calls),2)
        self.assertEqual(events[-1][1][0][0]['emotions'][0]['evidence'][0]['quote'],'furious with myself')

    def test_arc_incomplete_and_malformed_response(self):
        for reply in (lambda:self.response(example(),'length'),lambda:io.StringIO('{"choices":[]}')):
            with self.assertRaises(AnalysisError):
                analyze_batch(self.batch,'test',threading.Event(),opener=lambda *a,**k:reply(),provider='arc')

    def test_arc_auth_error_names_provider_without_secret(self):
        def send(*a,**k):
            raise urllib.error.HTTPError(ARC_ENDPOINT,401,'arc-secret',{},None)
        with self.assertRaises(AnalysisError) as error:
            analyze_batch(self.batch,'arc-secret',threading.Event(),opener=send,provider='arc')
        self.assertIn('VT ARC',str(error.exception))
        self.assertNotIn('arc-secret',str(error.exception))

    def test_arc_session_and_legacy_openai(self):
        data=export_session([self.batch[0]['text']],{1:example()},'ARC',{},provider='arc',model='custom-arc-model')
        self.assertEqual(data['provider'],'arc')
        self.assertEqual(data['model'],'custom-arc-model')
        self.assertEqual(load_session(data)[1][1]['id'],1)
        legacy=export_session([self.batch[0]['text']],{1:example()},'OpenAI',{})
        del legacy['provider']
        self.assertEqual(load_session(legacy)[1][1]['id'],1)
        data['provider']='unknown'
        with self.assertRaises(AnalysisError):load_session(data)


class TransportTests(unittest.TestCase):
    def test_mac_context_uses_system_bundle_with_verification(self):
        from unittest.mock import patch, MagicMock
        context=MagicMock()
        with patch('analysis.sys.platform','darwin'), patch('analysis.Path.is_file',return_value=True), \
             patch('analysis.ssl.SSLContext',return_value=context) as constructor, \
             patch('analysis.ssl.create_default_context') as defaults, \
             patch('analysis.urllib.request.urlopen') as send:
            secure_urlopen('https://example.invalid',15)
            constructor.assert_called_once_with(ssl.PROTOCOL_TLS_CLIENT)
            context.load_verify_locations.assert_called_once_with(cafile='/etc/ssl/cert.pem')
            defaults.assert_not_called()
            send.assert_called_once_with('https://example.invalid',timeout=15,context=context)

    def test_network_failures_are_not_all_reported_as_timeouts(self):
        batch=[{'id':1,'text':'Test.','context_before':'','context_after':''}]
        for error,expected in [(TimeoutError(),'timed out'),
                               (FileNotFoundError(2,'missing'),'certificate file'),
                               (ConnectionResetError(54,'reset'),'system error 54')]:
            def fail(*args,**kwargs):raise error
            with self.subTest(error=type(error).__name__),self.assertRaisesRegex(AnalysisError,expected):
                analyze_batch(batch,'test-secret',threading.Event(),opener=fail)


if __name__=='__main__':unittest.main()
