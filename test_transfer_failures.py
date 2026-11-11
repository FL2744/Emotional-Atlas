import threading
import unittest
from unittest.mock import patch
from analysis import AnalysisError, RequestError, Cancelled, analyze_resilient_batch
from shape_transfer import run_transfer, FLEXIBLE_REWRITE_PROMPT
from test_shape_transfer import row

class FailureContinuationTests(unittest.TestCase):
    def test_failed_stages_do_not_block_later_passages(self):
        for stage in ('baseline','rewrite','review','candidate','final'):
            with self.subTest(stage=stage):
                final=[False]
                def score(group,*args,**kwargs):
                    failing=any(r['id']==2 for r in group)
                    revised=any('Revised' in r['text'] for r in group)
                    if failing and ((stage=='baseline' and not revised) or
                                    (stage=='candidate' and revised and not final[0]) or
                                    (stage=='final' and final[0])):
                        raise AnalysisError('Invalid score fixture')
                    return [row(r['id']) for r in group],{}
                def request(prompt,payload,*args,**kwargs):
                    failing=any(r['id']==2 for r in payload['units'])
                    if failing and ((stage=='rewrite' and prompt==FLEXIBLE_REWRITE_PROMPT) or
                                    (stage=='review' and prompt!=FLEXIBLE_REWRITE_PROMPT)):
                        raise AnalysisError('Invalid response fixture')
                    if prompt==FLEXIBLE_REWRITE_PROMPT:
                        return {'units':[{'id':r['id'],'text':'Revised passage.','changes':'Changed.'} for r in payload['units']]},{}
                    return {'units':[{'id':r['id'],'reasonable':True,'meaning_preserved':False,'concerns':[]} for r in payload['units']]},{}
                records={}
                for kind,value in run_transfer([row(1),row(2)],2,'First.\n\nSecond.\n\nThird.','blank','offline',threading.Event(),score_fn=score,json_fn=request):
                    if kind=='status' and value.startswith('Final geometry'):final[0]=True
                    if kind=='unit':records[value['id']]=value
                self.assertEqual(set(records),{1,2,3})
                self.assertTrue(records[3]['accepted'])
                self.assertTrue(records[2]['processing_errors'])
                if stage!='final':self.assertEqual(records[2]['text'],'Second.')
                else:
                    self.assertEqual(records[2]['text'],'Revised passage.')
                    self.assertNotIn('final_score',records[2])

    def test_later_failed_attempt_keeps_accepted_revision(self):
        count=[0]
        def score(group,*args,**kwargs):return [row(r['id']) for r in group],{}
        def request(prompt,payload,*args,**kwargs):
            if prompt==FLEXIBLE_REWRITE_PROMPT:
                count[0]+=1
                if count[0]==2:raise AnalysisError('Invalid second attempt')
                return {'units':[{'id':1,'text':'Revised.','changes':'Changed.'}]},{}
            return {'units':[{'id':1,'reasonable':True,'meaning_preserved':False,'concerns':[]}]},{}
        events=list(run_transfer([row(1),row(2)],2,'Original.','blank','offline',threading.Event(),attempts=2,score_fn=score,json_fn=request))
        result=[v for k,v in events if k=='unit'][-1]
        self.assertEqual(result['text'],'Revised.')
        self.assertTrue(result['accepted']);self.assertTrue(result['processing_errors'])

    def test_request_errors_and_cancellation_still_stop(self):
        for exception in (RequestError('Account unavailable'),Cancelled()):
            def score(*args,**kwargs):raise exception
            with self.assertRaises(type(exception)):
                list(run_transfer([row(1),row(2)],2,'Original.','blank','offline',threading.Event(),score_fn=score))

    def test_analysis_flags_bad_response_and_continues(self):
        group=[{'id':1,'text':'First.'},{'id':2,'text':'Second.'}]
        def analyze(batch,*args,**kwargs):
            if len(batch)>1 or batch[0]['id']==1:raise AnalysisError('Malformed response')
            return [row(2)],{}
        with patch('analysis.analyze_batch',side_effect=analyze):
            events=list(analyze_resilient_batch(group,'offline',threading.Event()))
        self.assertEqual([v[0] for k,v in events if k=='review'],[1])
        self.assertEqual([v[0][0]['id'] for k,v in events if k=='result'],[2])
