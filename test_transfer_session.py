import copy
import json
import tempfile
import threading
import unittest
from pathlib import Path
from analysis import AnalysisError
from shape_transfer import run_transfer,FLEXIBLE_REWRITE_PROMPT
from transfer_session import checkpoint,restore,write_checkpoint
from test_shape_transfer import row

class TransferCheckpointTests(unittest.TestCase):
    def setUp(self):
        self.source={'rows':[row(1),row(2)],'total':2,'title':'Dream','segmentation':'blank','provider':'openai','model':'gpt-6-luna'}
        self.signature=('First.\n\nSecond.','blank','100%','1','Flexible transformation')
        self.calls=[]
        def score(group,*args,**kwargs):return [row(r['id']) for r in group],{}
        def request(prompt,payload,*args,**kwargs):
            if prompt==FLEXIBLE_REWRITE_PROMPT:
                self.calls.extend(r['id'] for r in payload['units'])
                return {'units':[{'id':r['id'],'text':'Revised.','changes':'Changed.'} for r in payload['units']]},{}
            return {'units':[{'id':r['id'],'reasonable':True,'meaning_preserved':False,'concerns':[]} for r in payload['units']]},{}
        self.score=score;self.request=request
        events=self.transfer()
        self.records={v['id']:v for k,v in events if k=='unit'}
        self.data=checkpoint(self.source,self.signature,{1:self.records[1]},{'input_tokens':2,'output_tokens':3})
    def transfer(self,completed=None):
        return list(run_transfer(self.source['rows'],2,self.signature[0],'blank','offline',threading.Event(),score_fn=self.score,json_fn=self.request,completed=completed))
    def test_roundtrip_and_resume_skips_saved_work(self):
        restored=restore(json.loads(json.dumps(self.data)))
        self.assertEqual(restored['signature'],self.signature)
        self.assertEqual(restored['source'],self.source)
        self.calls.clear();events=self.transfer(restored['records'])
        self.assertEqual(self.calls,[2])
        self.assertEqual({v['id'] for k,v in events if k=='unit'},{2})
    def test_snapshot_is_independent(self):
        self.records[1]['text']='Later change'
        self.assertEqual(self.data['records']['1']['text'],'Revised.')
        self.assertNotIn('offline',json.dumps(self.data))
    def test_reject_mismatched_original_and_invalid_ids(self):
        broken=copy.deepcopy(self.data);broken['records']['1']['original']='Different document'
        with self.assertRaises(AnalysisError):restore(broken)
        broken=copy.deepcopy(self.data);broken['records']['9']=broken['records'].pop('1')
        with self.assertRaises(AnalysisError):restore(broken)
    def test_draft_and_complete_checkpoints(self):
        empty=checkpoint(self.source,self.signature,{}, {'input_tokens':0,'output_tokens':0})
        self.assertFalse(restore(empty)['finished'])
        complete=checkpoint(self.source,self.signature,self.records,{'input_tokens':2,'output_tokens':3},True)
        self.assertTrue(restore(complete)['finished'])
        empty['complete']=True
        with self.assertRaises(AnalysisError):restore(empty)
    def test_failed_save_preserves_existing_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'transfer.json';write_checkpoint(path,self.data)
            before=path.read_bytes();broken=copy.deepcopy(self.data);broken['usage']['input_tokens']=float('nan')
            with self.assertRaises(ValueError):write_checkpoint(path,broken)
            self.assertEqual(path.read_bytes(),before)
            self.assertEqual(len(list(Path(directory).iterdir())),1)
