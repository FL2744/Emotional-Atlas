import unittest
from session_identity import session_identity, session_filename
from analysis import export_session, load_session

class SessionIdentityTests(unittest.TestCase):
    def test_distinct_and_restored(self):
        first = session_identity('Dream')
        second = session_identity('Dream')
        self.assertNotEqual(first['session_id'], second['session_id'])
        self.assertNotEqual(first['session_name'], second['session_name'])
        self.assertEqual(session_identity('Dream', first), first)

    def test_save_and_legacy(self):
        identity = session_identity('Dream', {'created_at':'2025-01-01T12:00:00+00:00'})
        data = export_session(['A dream.'], {}, 'Dream', {}, identity=identity)
        again = export_session(['A dream.'], {}, 'Dream', {}, identity=data)
        self.assertEqual(data['created_at'], again['created_at'])
        self.assertEqual(data['session_id'], again['session_id'])
        self.assertEqual(load_session(data)[0], ['A dream.'])
        self.assertIn('saved_at', again)
        self.assertTrue(identity['created_at'].startswith('2025-01-01'))

    def test_filenames(self):
        identity = session_identity('A/B: dream?')
        first = session_filename(identity, '2026-11-10T12:00:00.000001+00:00')
        second = session_filename(identity, '2026-11-10T12:00:00.000002+00:00')
        self.assertNotEqual(first, second)
        self.assertNotIn('/', first)
        self.assertNotIn(':', first)
