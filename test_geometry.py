import json
import unittest
import numpy as np
from geometry import METHODS, mesh, frame_mesh, obj_text, description

class GeometryTests(unittest.TestCase):
    def setUp(self):
        self.cube=[[x,y,z] for x in (-1,1) for y in (-1,1) for z in (-1,1)]
        self.tetra=[[0,0,0],[1,0,0],[0,1,0],[0,0,1]]

    def test_cube_hull_and_halfspaces(self):
        result=mesh(self.cube+[[0,0,0],self.cube[0]])
        self.assertAlmostEqual(result['volume'],8)
        self.assertAlmostEqual(result['area'],24)
        self.assertEqual(len(result['faces']),12)
        self.assertTrue(result['closed_edge_manifold'])
        for equation in result['halfspaces']:
            for point in self.cube:self.assertLessEqual(np.dot(equation[:3],point)+equation[3],1e-10)
        self.assertEqual(len(result['paragraph_ids']),10)

    def test_orientations_and_obj(self):
        result=mesh(self.tetra);vertices=np.array(result['vertices'])
        signed=sum(np.dot(vertices[a],np.cross(vertices[b],vertices[c]))/6 for a,b,c in result['faces'])
        self.assertAlmostEqual(signed,1/6)
        self.assertAlmostEqual(result['volume'],1/6)
        text=obj_text(result)
        self.assertEqual(sum(line.startswith('f ') for line in text.splitlines()),4)
        json.dumps(result,allow_nan=False)

    def test_neighbor_limit_and_disconnected_solids(self):
        result=mesh(self.tetra,METHODS[1],1.5)
        self.assertAlmostEqual(result['volume'],1/6)
        self.assertEqual(len(result['faces']),4)
        result=mesh(self.tetra,METHODS[1],.5)
        self.assertEqual(result['volume'],0);self.assertEqual(result['faces'],[])
        separated=self.tetra+[[x+10,y,z] for x,y,z in self.tetra]
        result=mesh(separated,METHODS[1],1.5)
        self.assertAlmostEqual(result['volume'],1/3)
        self.assertEqual(len(result['faces']),8)

    def test_degeneracy_and_invalid_coordinates(self):
        for points in ([],[[0,0,0]],[[0,0,0]]*5,[[0,0,0],[1,0,0],[0,1,0],[1,1,0]]):
            result=mesh(points);self.assertFalse(result['faces']);self.assertIsNone(result['volume'])
        with self.assertRaises(ValueError):mesh([[float('nan'),0,0]])
        with self.assertRaises(ValueError):mesh(self.tetra,radius=0)

    def test_tube_caps_gaps_and_repeated_centers(self):
        result=mesh([[0,0,0],[0,0,1],[0,0,1],[0,0,2]],METHODS[2],.1)
        self.assertTrue(result['closed_edge_manifold']);self.assertIsNone(result['volume'])
        self.assertTrue(np.isfinite(result['vertices']).all())
        broken=mesh([[0,0,0],[0,0,1]],METHODS[2],.1,ids=[1,3])
        self.assertFalse(broken['faces'])

    def test_temporal_windows_use_paragraph_positions(self):
        samples=[{'id':i+1,'point':p} for i,p in enumerate(self.cube)]
        full=frame_mesh(samples,8,'Cumulative',4,METHODS[0],1)
        early=frame_mesh(samples,1,'Cumulative',4,METHODS[0],1)
        self.assertEqual(full['volume'],8);self.assertFalse(early['faces'])
        later=frame_mesh(samples,8,'Moving window',4,METHODS[0],1)
        self.assertEqual(later['paragraph_ids'],[5,6,7,8])
        missing=frame_mesh(samples[:2]+samples[5:],6,'Moving window',3,METHODS[0],1)
        self.assertEqual(missing['paragraph_ids'],[6])
        self.assertEqual(frame_mesh(samples,1,'Whole text',1,METHODS[0],1)['volume'],8)

class CurvedSurfaceTests(unittest.TestCase):
    def test_subdivision_counts_and_metrics(self):
        from geometry import curved_surface
        base=mesh([[0,0,0],[1,0,0],[0,1,0],[0,0,1]])
        smooth=curved_surface(base,2)
        self.assertEqual(len(smooth['faces']),64)
        self.assertEqual(len(base['faces']),4)
        self.assertGreater(smooth['volume'],0)
        self.assertLess(smooth['volume'],base['volume'])
        self.assertIn('control_halfspaces',smooth)
        self.assertNotIn('halfspaces',smooth)
        self.assertTrue(np.isfinite(smooth['vertices']).all())
        from collections import Counter
        edges=Counter(tuple(sorted((f[i],f[(i+1)%3]))) for f in smooth['faces'] for i in range(3))
        self.assertTrue(all(n==2 for n in edges.values()))

    def test_degenerate_and_open_surface(self):
        from geometry import curved_surface
        self.assertEqual(curved_surface(mesh([[0,0,0]]))['faces'],[])
        broken=mesh([[0,0,0],[1,0,0],[0,1,0],[0,0,1]])
        broken['faces'].pop()
        with self.assertRaises(ValueError):curved_surface(broken)

    def test_material_and_description(self):
        from geometry import curved_surface,material_text
        self.assertIn('Kd 1.00000000 0.00000000 0.00000000',material_text('#ff0000'))
        model=curved_surface(mesh([[0,0,0],[1,0,0],[0,1,0],[0,0,1]]))
        report=description(model,dict(coordinates='test',evolution='Cumulative',frame=4,total=4,window=4,surface_color='#ff0000'))
        self.assertIn('Loop subdivision, 2',report);self.assertIn('#ff0000',report)

if __name__=='__main__':unittest.main()
