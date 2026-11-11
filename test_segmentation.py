import unittest
from analysis import split_paragraphs, export_session, load_session, batches, AnalysisError

class SegmentationTests(unittest.TestCase):
    def test_default_unchanged(self):
        self.assertEqual(split_paragraphs('I was sad. Then relieved.\n\nNext paragraph.'),['I was sad. Then relieved.','Next paragraph.'])
    def test_sentence_punctuation_and_evidence_preserved(self):
        text='Dr. Smith paid 3.50 dollars. “I feel happy!” Then I woke up.'
        self.assertEqual(split_paragraphs(text,'sentence'),['Dr. Smith paid 3.50 dollars.','“I feel happy!”','Then I woke up.'])
        for segment in split_paragraphs(text,'sentence'):self.assertIn(segment,text)
    def test_multilingual_and_final_fragment(self):
        self.assertEqual(split_paragraphs('我很害怕。后来安心了！هل أنت بخير؟ نعم. Final fragment','sentence'),['我很害怕。','后来安心了！','هل أنت بخير؟','نعم.','Final fragment'])
    def test_context_is_neighboring_sentence(self):
        rows=list(batches(split_paragraphs('Sad. Afraid! Relieved.','sentence')))[0]
        self.assertEqual(rows[1]['text'],'Afraid!')
        self.assertEqual(rows[1]['context_before'],'Sad.')
        self.assertEqual(rows[1]['context_after'],'Relieved.')
    def test_session_mode_and_legacy(self):
        text='One. Two.';segments=split_paragraphs(text,'sentence')
        data=export_session(segments,{},'test',{},segmentation='sentence',source_text=text)
        self.assertEqual(load_session(data)[0],segments)
        self.assertEqual(data['segmentation'],'sentence')
        self.assertEqual(data['source_text'],text)
        data.pop('segmentation');data.pop('source_text');self.assertEqual(load_session(data)[0],segments)
        data['segmentation']='unknown'
        with self.assertRaises(AnalysisError):load_session(data)

if __name__=='__main__':unittest.main()
