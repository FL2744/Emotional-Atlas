import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch
from evolution_export import write_evolution, ExportCancelled
from geometry import METHODS

class EvolutionExportTests(unittest.TestCase):
    def setUp(self):
        self.meta={'total':1000,'evolution':'Cumulative','window':10,'method':METHODS[0],'size':1,'subdivision_levels':2}
        self.source=[{'id':i+1,'point':p} for i,p in enumerate([[0,0,0],[1,0,0],[0,1,0],[0,0,1]])]
    def test_compact_never_computes_meshes_and_keeps_every_frame(self):
        with tempfile.TemporaryDirectory() as tmp, patch('evolution_export.frame_mesh',side_effect=AssertionError('must not compute')):
            path=Path(tmp)/'out.json'
            write_evolution(path,self.meta,self.source,'definition','Compact · all paragraphs',threading.Event())
            data=json.loads(path.read_text())
            self.assertEqual(len(data['frames']),1000)
            self.assertEqual(data['frames'][-1]['tau'],1)
            self.assertEqual(data['source_samples'],self.source)
            self.assertLess(path.stat().st_size,100000)
    def test_cancel_is_atomic(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'out.json';path.write_text('previous export')
            cancel=threading.Event()
            with self.assertRaises(ExportCancelled):
                write_evolution(path,self.meta,self.source,'definition','Compact · all paragraphs',cancel,lambda s:cancel.set())
            self.assertEqual(path.read_text(),'previous export')
            self.assertEqual(list(Path(tmp).iterdir()),[path])
    def test_sample_cap_and_endpoints(self):
        with tempfile.TemporaryDirectory() as tmp, patch('evolution_export.frame_mesh',return_value={'faces':[],'vertices':[]}) as build:
            path=Path(tmp)/'out.json'
            write_evolution(path,self.meta,self.source,'definition','Sampled meshes · up to 60',threading.Event())
            data=json.loads(path.read_text())
            self.assertEqual(build.call_count,60)
            self.assertEqual(data['mesh_paragraphs'][0],1)
            self.assertEqual(data['mesh_paragraphs'][-1],1000)
            self.assertEqual(len(data['frames']),1000)
    def test_mesh_budget_preserves_destination(self):
        with tempfile.TemporaryDirectory() as tmp, patch('evolution_export.frame_mesh',return_value={'faces':[[0,1,2]]*2000}):
            path=Path(tmp)/'out.json';path.write_text('original')
            with self.assertRaises(ValueError):write_evolution(path,self.meta,self.source,'definition','Sampled meshes · up to 60',threading.Event())
            self.assertEqual(path.read_text(),'original')

if __name__=='__main__':unittest.main()
