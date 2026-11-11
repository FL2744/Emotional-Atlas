import threading
import unittest
from analysis import AnalysisError,Cancelled
from shape_transfer import trajectory,align,distance,prepare,run_transfer,REWRITE_PROMPT,FLEXIBLE_REWRITE_PROMPT,target_layout,assemble_target,transfer_batches


def row(i,v=0,d=0,intensity=.5):
    return {'id':i,'valence':v,'direction':d,'intensity':intensity,'direction_status':'mixed','tone':'mixed',
            'uncertainty':'medium','summary':'Offline fixture','uncertainty_note':'','emotions':[]}

class TransferTests(unittest.TestCase):
    def setUp(self):self.source=[row(1,.8,.8,.8),row(2,.8,.8,.8)]
    def test_alignment_and_normalized_distance(self):
        knots=trajectory([row(1,-1,-1,0),row(3,1,1,1)],3)
        self.assertEqual(align(knots,3),[[-1,-1,-1],[0,0,0],[1,1,1]])
        self.assertEqual(align(knots,1),[[0,0,0]])
        self.assertAlmostEqual(distance(row(1,-1,-1,0),[1,1,1]),1)
        self.assertIsNone(distance(row(1,d=None),[0,0,0]))
    def test_source_and_target_limits(self):
        with self.assertRaises(AnalysisError):trajectory([row(1,d=None)],1)
        units=prepare(self.source,2,'X'*6001,'blank')[0]
        self.assertEqual(''.join(units),'X'*6001)
        self.assertLessEqual(max(map(len,units)),3000)
        self.assertEqual(len(prepare(self.source,2,'One. Two!','sentence')[0]),2)
    def test_long_document_preserves_structure(self):
        text='  '+('A sentence about a dream. '*4000)+'\r\n\r\nSecond paragraph.\n'
        for mode in ('blank','sentence'):
            spans=target_layout(text,mode)
            units,_,desired=prepare(self.source,2,text,mode)
            self.assertEqual(assemble_target(text,spans,{}),text)
            self.assertEqual(len(units),len(desired))
            self.assertLessEqual(max(map(len,units)),3000)
            for group in transfer_batches(units):
                self.assertLessEqual(sum(len(r['text']) for r in group),6000)
            first_start,first_end=spans[0]
            self.assertEqual(assemble_target(text,spans,{1:{'text':'Revised.'}}),text[:first_start]+'Revised.'+text[first_end:])

    def test_multilingual_long_units(self):
        for text in ('梦中的门开了。'*2000, 'كان الباب مفتوحا؟ '*1000, 'x'*10000):
            spans=target_layout(text,'blank')
            self.assertEqual(assemble_target(text,spans,{}),text)
            self.assertTrue(all(0<end-start<=3000 for start,end in spans))

    def test_multibatch_transfer_and_resume_keep_all_passages(self):
        text='A door was open. '*1500
        units=prepare(self.source,2,text,'blank')[0]
        requests=[]
        def score(group,*args,**kwargs):return [row(r['id']) for r in group],{}
        def request(prompt,payload,*args,**kwargs):
            if prompt==REWRITE_PROMPT:
                requests.extend(r['id'] for r in payload['units'])
                return {'units':[{'id':r['id'],'text':r['text'],'changes':'Retained original.'} for r in payload['units']]},{}
            return {'units':[{'id':r['id'],'meaning_preserved':True,'concerns':[]} for r in payload['units']]},{}
        records={}
        for kind,value in run_transfer(self.source,2,text,'blank','offline',threading.Event(),preservation='strict',score_fn=score,json_fn=request):
            if kind=='unit':records[value['id']]=value
        self.assertEqual(requests,list(range(1,len(units)+1)))
        self.assertTrue(all('final_score' in r for r in records.values()))
        self.assertEqual(assemble_target(text,target_layout(text,'blank'),records),text)
        completed={i:records[i] for i in range(1,4)};requests.clear()
        for kind,value in run_transfer(self.source,2,text,'blank','offline',threading.Event(),preservation='strict',score_fn=score,json_fn=request,completed=completed):
            if kind=='unit':completed[value['id']]=value
        self.assertEqual(requests,list(range(4,len(units)+1)))
        self.assertEqual(assemble_target(text,target_layout(text,'blank'),completed),text)

    def execute(self,faithful=True,candidate_value=.7,attempts=1,completed=None):
        calls=[];scores=[]
        def score(group,*args,**kwargs):
            scores.append(group)
            return [row(r['id'],candidate_value,.8,.8) if 'stood' in r['text'] else row(r['id'],-.8,-.8,.2) for r in group],{'input_tokens':1,'output_tokens':2}
        def request(prompt,payload,*args,**kwargs):
            calls.append(payload)
            if prompt==REWRITE_PROMPT:
                return {'units':[{'id':r['id'],'text':'The door stood open.','changes':'Changed phrasing.'} for r in payload['units']]},{'input_tokens':1}
            return {'units':[{'id':r['id'],'meaning_preserved':faithful,'concerns':[] if faithful else ['Meaning changed.']} for r in payload['units']]},{'input_tokens':1}
        events=list(run_transfer(self.source,2,'The door was open.','blank','offline',threading.Event(),preservation='strict',score_fn=score,json_fn=request,attempts=attempts,completed=completed))
        records=[v for k,v in events if k=='unit']
        return records,calls,scores
    def test_faithful_improvement_is_scored_and_retained(self):
        records,calls,scores=self.execute()
        self.assertTrue(records[-1]['accepted']);self.assertIn('stood',records[-1]['text'])
        self.assertLess(records[-1]['final_error'],records[-1]['before_error'])
        self.assertEqual(len(scores),3) # baseline, candidate, final assembled context
        self.assertNotIn('desired',scores[-1][0])
    def test_semantic_failure_retains_original(self):
        records,_,_=self.execute(faithful=False)
        self.assertFalse(records[-1]['accepted']);self.assertEqual(records[-1]['text'],'The door was open.')
    def test_attempt_bound_and_resume(self):
        records,calls,_=self.execute(attempts=2)
        self.assertEqual(len(calls),4)
        resumed,resume_calls,scores=self.execute(completed={1:records[-1]})
        self.assertEqual(resume_calls,[]);self.assertEqual(len(scores),0) # completed final scoring is not billed again
    def test_unchanged_geometry_does_not_accept_a_revision(self):
        def score(group,*args,**kwargs):return [row(r['id'],.8,.8,.8) for r in group],{}
        def request(prompt,payload,*args,**kwargs):
            if prompt==REWRITE_PROMPT:return {'units':[{'id':1,'text':'The door stood open.','changes':'Diction'}]},{}
            return {'units':[{'id':1,'meaning_preserved':True,'concerns':[]}]},{}
        events=list(run_transfer(self.source,2,'The door was open.','blank','offline',threading.Event(),preservation='strict',score_fn=score,json_fn=request))
        self.assertFalse([v for k,v in events if k=='unit'][-1]['accepted'])

    def test_numeric_change_overrides_model_fidelity_claim(self):
        calls=[0]
        def score(group,*args,**kwargs):
            calls[0]+=1
            return [row(1,-.8,-.8,.2) if calls[0]==1 else row(1,.8,.8,.8)],{}
        def request(prompt,payload,*args,**kwargs):
            if prompt==REWRITE_PROMPT:return {'units':[{'id':1,'text':'There were 3 doors.','changes':'Diction'}]},{}
            return {'units':[{'id':1,'meaning_preserved':True,'concerns':[]}]},{}
        events=list(run_transfer(self.source,2,'There were 2 doors.','blank','offline',threading.Event(),preservation='strict',score_fn=score,json_fn=request))
        record=[v for k,v in events if k=='unit'][-1]
        self.assertFalse(record['accepted']);self.assertIn('Numeric',record['attempts'][0]['meaning_review']['concerns'][0])

    def test_flexible_selects_closest_reasonable_mutation(self):
        trial=[0]
        def score(group,*args,**kwargs):
            return [row(1,.8,.8,.8) if r['text']=='Original.' else row(1,.3 if '3' in r['text'] else .6,.8,.8) for r in group],{}
        def request(prompt,payload,*args,**kwargs):
            if prompt==FLEXIBLE_REWRITE_PROMPT:
                trial[0]+=1
                return {'units':[{'id':1,'text':f"The {4-trial[0]} doors glowed.",'changes':'Changed imagery and details.'}]},{}
            return {'units':[{'id':1,'reasonable':True,'meaning_preserved':False,'concerns':['Changed events.']}]},{}
        events=list(run_transfer(self.source,2,'Original.','blank','offline',threading.Event(),attempts=2,score_fn=score,json_fn=request))
        record=[v for k,v in events if k=='unit'][-1]
        self.assertTrue(record['accepted'])
        self.assertEqual(record['text'],'The 2 doors glowed.')
        self.assertGreater(record['after_error'],record['before_error'])
        self.assertFalse(record['attempts'][-1]['meaning_review']['meaning_preserved'])

    def test_flexible_rejects_unreasonable_replacement(self):
        def score(group,*args,**kwargs):return [row(r['id']) for r in group],{}
        def request(prompt,payload,*args,**kwargs):
            if prompt==FLEXIBLE_REWRITE_PROMPT:return {'units':[{'id':1,'text':'Unrelated replacement.','changes':'Changed subject.'}]},{}
            return {'units':[{'id':1,'reasonable':False,'meaning_preserved':False,'concerns':['Unrelated.']}]},{}
        events=list(run_transfer(self.source,2,'Original.','blank','offline',threading.Event(),score_fn=score,json_fn=request))
        self.assertFalse([v for k,v in events if k=='unit'][-1]['accepted'])

    def test_rewrite_can_change_sentence_and_paragraph_boundaries(self):
        for mode in ('blank','sentence'):
            for policy in ('flexible','strict'):
                with self.subTest(mode=mode,policy=policy):
                    replacement='The door opened. Light poured in.\n\nI stepped toward it.'
                    scored=[]
                    def score(group,*args,**kwargs):
                        scored.extend(group)
                        return [row(r['id'],.8,.8,.8) if r['text']==replacement else row(r['id'],-.8,-.8,.2) for r in group],{}
                    def request(prompt,payload,*args,**kwargs):
                        if prompt in (REWRITE_PROMPT,FLEXIBLE_REWRITE_PROMPT):
                            return {'units':[{'id':1,'text':replacement,'changes':'Changed sentence boundaries.'}]},{}
                        review={'id':1,'meaning_preserved':True,'concerns':[]}
                        if policy=='flexible':review['reasonable']=True
                        return {'units':[review]},{}
                    events=list(run_transfer(self.source,2,'The door was open.','%s'%mode,'offline',threading.Event(),preservation=policy,score_fn=score,json_fn=request))
                    records={v['id']:v for k,v in events if k=='unit'}
                    self.assertEqual(list(records),[1])
                    self.assertTrue(records[1]['accepted'])
                    self.assertEqual(assemble_target('The door was open.',target_layout('The door was open.',mode),records),replacement)
                    self.assertEqual(scored[-1]['text'],replacement)
                    self.assertIn('final_score',records[1])

    def test_cancel_before_requests(self):
        cancel=threading.Event();cancel.set()
        with self.assertRaises(Cancelled):list(run_transfer(self.source,2,'Target.','blank','offline',cancel))

if __name__=='__main__':unittest.main()
