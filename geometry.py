"""Deterministic solids in the plot coordinate system and discrete spacetime slices."""
from collections import Counter
import math
import numpy as np
from scipy.spatial import ConvexHull, Delaunay, QhullError

METHODS = ('Outermost points', 'Spatial neighbors', 'Text-order tube')


def orient(face, points, inside):
    a,b,c=face
    if np.dot(np.cross(points[b]-points[a],points[c]-points[a]),inside-points[a])>0:b,c=c,b
    return [int(a),int(b),int(c)]


def mesh(points, method=METHODS[0], radius=1.0, ids=None):
    """Hull, boundary of edge-limited Delaunay tetrahedra, or capped path tube.

    No jitter, rescaling, inferred coordinates, or silent point sampling.
    """
    if method not in METHODS:raise ValueError('Unknown construction method.')
    if not math.isfinite(radius) or radius<=0:raise ValueError('Size must be positive and finite.')
    p=np.asarray(points,dtype=float).reshape((-1,3))
    if not np.isfinite(p).all():raise ValueError('Coordinates must be finite.')
    ids=list(range(1,len(p)+1)) if ids is None else list(ids)
    if len(ids)!=len(p):raise ValueError('One paragraph ID is required per point.')
    result={'method':method,'size':radius,'input_points':p.tolist(),'paragraph_ids':ids,
            'vertices':[], 'faces':[], 'tetrahedra':[], 'halfspaces':[], 'area':0.0,
            'volume':None,'closed_edge_manifold':False,'message':'','rank':0}
    if not len(p):result['message']='No eligible points in this slice.';return result
    unique=np.unique(p,axis=0)
    result['rank']=int(np.linalg.matrix_rank(unique-unique[0],tol=1e-10))
    if method==METHODS[2]:
        vertices,faces=tube(p,ids,radius)
        result['vertices']=vertices;result['faces']=faces
        result['message']='Tube thickness is chosen by you. Self-intersections are possible; enclosed volume is not reported.'
    else:
        result['vertices']=unique.tolist()
        if len(unique)<4 or result['rank']<3:
            result['message']='A solid needs four noncoplanar unique points. This slice is a point, line, or plane; no thickness was invented.'
            return result
        try:
            if method==METHODS[0]:
                hull=ConvexHull(unique)
                result['faces']=[orient(f,unique,unique.mean(axis=0)) for f in hull.simplices]
                result['halfspaces']=hull.equations.tolist()
                result['volume']=float(hull.volume)
            else:
                triangulation=Delaunay(unique)
                boundary={};volume=0.0;tetrahedra=[]
                for tet in triangulation.simplices:
                    q=unique[tet]
                    if max(np.linalg.norm(q[i]-q[j]) for i in range(4) for j in range(i))>radius:continue
                    v=abs(np.linalg.det((q[1:]-q[0]).T))/6
                    if v<=1e-14:continue
                    tetrahedra.append([int(i) for i in tet]);volume+=v
                    for k in range(4):
                        face=[int(tet[j]) for j in range(4) if j!=k];key=tuple(sorted(face))
                        if key in boundary:del boundary[key]
                        else:boundary[key]=orient(face,unique,unique[tet[k]])
                result['tetrahedra']=tetrahedra;result['faces']=list(boundary.values());result['volume']=float(volume)
                result['message']='Local Delaunay neighbors; gaps, cavities and disconnected components are allowed.' if tetrahedra else 'No neighboring tetrahedra fit this edge limit. Increase the size control.'
        except QhullError:
            result['message']='Numerically degenerate geometry. No solid was generated; coordinates were not perturbed.'
            return result
    v=np.asarray(result['vertices']);faces=result['faces']
    result['area']=float(sum(np.linalg.norm(np.cross(v[b]-v[a],v[c]-v[a]))/2 for a,b,c in faces))
    edges=Counter(tuple(sorted((face[i],face[(i+1)%3]))) for face in faces for i in range(3))
    result['closed_edge_manifold']=bool(edges) and all(n==2 for n in edges.values())
    result['boundary_edges']=sum(n==1 for n in edges.values())
    result['nonmanifold_edges']=sum(n>2 for n in edges.values())
    if faces and not result['closed_edge_manifold']:
        result['message']+=' Surface has nonmanifold contacts; inspect before fabrication.'
    return result


def tube(p,ids,radius,sides=12):
    """Capped polygonal rings along consecutive paragraph centers; break at missing IDs.

    Rotation-minimizing transported frames reduce twist. Repeated centers are
    skipped within runs. Mesh can self-intersect at tight bends or crossings.
    """
    runs=[];run=[]
    for i,q in enumerate(p):
        if i and ids[i]!=ids[i-1]+1:
            if run:runs.append(run)
            run=[]
        if not run or np.linalg.norm(q-run[-1])>1e-10:run.append(q)
    if run:runs.append(run)
    vertices=[];faces=[]
    for run in runs:
        if len(run)<2:continue
        base=len(vertices);previous=None
        for i,q in enumerate(run):
            delta=run[min(i+1,len(run)-1)]-run[max(0,i-1)]
            if np.linalg.norm(delta)<1e-10:delta=run[i]-run[i-1]
            tangent=delta/np.linalg.norm(delta)
            u=previous-tangent*np.dot(previous,tangent) if previous is not None else np.zeros(3)
            if np.linalg.norm(u)<1e-8:
                axis=np.eye(3)[int(np.argmin(np.abs(tangent)))];u=np.cross(tangent,axis)
            u/=np.linalg.norm(u);v=np.cross(tangent,u);previous=u
            vertices.extend((q+radius*(math.cos(j*2*math.pi/sides)*u+math.sin(j*2*math.pi/sides)*v)).tolist() for j in range(sides))
        for i in range(len(run)-1):
            for j in range(sides):
                a=base+i*sides+j;b=base+i*sides+(j+1)%sides;c=b+sides;d=a+sides
                faces.extend(([a,b,c],[a,c,d]))
        start=len(vertices);vertices.append(run[0].tolist());end=len(vertices);vertices.append(run[-1].tolist())
        last=base+(len(run)-1)*sides
        for j in range(sides):
            faces.append([start,base+(j+1)%sides,base+j])
            faces.append([end,last+j,last+(j+1)%sides])
    return vertices,faces


def slice_points(samples,frame,evolution,window):
    if evolution=='Whole text':return samples
    first=max(1,frame-window+1) if evolution=='Moving window' else 1
    return [r for r in samples if first<=r['id']<=frame]


def frame_mesh(samples,frame,evolution,window,method,size):
    subset=slice_points(samples,frame,evolution,window)
    return mesh([r['point'] for r in subset],method,size,[r['id'] for r in subset])


def description(model,metadata):
    method=model['method']
    definition={METHODS[0]:'S = conv{p_i} = {sum_i lambda_i p_i : lambda_i >= 0, sum_i lambda_i = 1}. Exported halfspaces satisfy n.x + b <= 0.',
        METHODS[1]:'Let D be the 3D Delaunay tetrahedralization of unique p_i. S = union{T in D : max edge length(T) <= L}. The surface consists of triangle faces incident to exactly one retained tetrahedron. L is the size setting.',
        METHODS[2]:'A 12-sided circular ring of radius r is swept along consecutive paragraph centers with transported normal frames. Adjacent rings are triangulated and each run is capped. Missing paragraph IDs break the path. Repeated centers are skipped. This is a geometric tube mesh; self-intersections may occur.'}[method]
    report=('Emotional Atlas — object description\n\n'+definition+'\n\n'
        'Surface color: '+metadata.get('surface_color','#cccccc')+' (one base color; lighting changes brightness only).\n'
        +('Loop subdivision, '+str(model.get('subdivision_levels',0))+' iterations. Edge vertex = 3/8(a+b)+1/8(c+d); old vertex = (1-n*beta)v + beta*sum(neighbors), beta=3/16 for n=3, otherwise 3/(8n). Each triangle becomes four. The displayed/exported mesh approximates the curved limit surface and can shrink. Hull inequalities/tetrahedra describe the control mesh only.\n' if model.get('subdivision_levels',0) else 'Faceted control surface.\n')
        +'Coordinates: '+metadata['coordinates']+'\n'
        'Source: snapshot of all analyzed paragraphs with finite 3D coordinates; the main plot filter is not applied.\n'
        f"Evolution: {metadata['evolution']}; frame {metadata['frame']} of {metadata['total']}; window {metadata['window']} paragraph positions.\n"
        'Fourth coordinate: tau_i=(i-1)/(N-1), with tau=0 for N=1. Paragraph order is time, not physical time. '
        'For cumulative mode, S_i uses paragraph IDs <= i. For moving-window mode, S_i uses max(1,i-w+1) <= ID <= i. '
        'The 4D object is the piecewise-constant occupied set W = union_{i=1}^{N-1} (S_i x [tau_i,tau_{i+1})), plus S_N at tau_N (zero for N=1, otherwise one). '
        'No interpolation of unmatched mesh vertices is assumed. Whole-text mode is a static 3D object.\n\n'
        f"Unique-coordinate rank: {model['rank']}; vertices: {len(model['vertices'])}; triangles: {len(model['faces'])}.\n"
        f"Surface area: {model['area']:.9g} coordinate-units squared.\n"
        f"Volume: {model['volume'] if model['volume'] is not None else 'not defined/reported'} coordinate-units cubed.\n"
        f"Every surface edge has two incident triangles: {model['closed_edge_manifold']} (not a proof of no self-intersections).\n"
        f"Size setting: {model['size']}. {model['message']}\n\n"
        'These are geometric descriptors of model-derived emotional scores, not physical or psychological measurements. '
        'Changing coordinate scaling, neighborhood size, window length or construction changes the object. Duplicate positions are merged for hull/tetrahedra but retain their paragraph IDs in source samples.\n')

    return report.replace('paragraph','sentence').replace('Paragraph','Sentence') if metadata.get('text_unit')=='sentence' else report


def obj_text(model):
    if not model['faces']:raise ValueError('This slice has no solid surface to export.')
    return '# Emotional Atlas; plot-coordinate units; triangle faces\n'+'\n'.join('v '+' '.join(format(x,'.17g') for x in p) for p in model['vertices'])+'\n'+'\n'.join('f '+' '.join(str(i+1) for i in f) for f in model['faces'])+'\n'


def curved_surface(model, levels=2, cancel=None):
    """Finite Loop subdivision: a triangulated approximation to a smooth limit surface."""
    import copy
    def checkpoint():
        if cancel is not None and cancel.is_set():
            from evolution_export import ExportCancelled
            raise ExportCancelled()
    checkpoint()
    if type(levels) is not int or not 0<=levels<=3:raise ValueError('Subdivision level must be 0–3.')
    result=copy.deepcopy(model);result['subdivision_levels']=levels
    if levels==0 or not model['faces']:return result
    if len(model['faces'])*4**levels>120000:raise ValueError('Curved surface would exceed 120,000 triangles. Choose lower smoothness or a shorter window.')
    v=np.array(model['vertices'],dtype=float);f=model['faces']
    for _ in range(levels):
        checkpoint()
        edges={};neighbors=[set() for p in v];links=[{} for p in v]
        for face_number,(a,b,c) in enumerate(f):
            if face_number%256==0:checkpoint()
            for i,j,k in ((a,b,c),(b,c,a),(c,a,b)):
                edges.setdefault(tuple(sorted((i,j))),[]).append(k)
                neighbors[i].update((j,k))
                links[i].setdefault(j,set()).add(k);links[i].setdefault(k,set()).add(j)
        if any(len(opposite)!=2 for opposite in edges.values()):raise ValueError('Curved surfaces require a closed manifold mesh. Adjust the neighbor limit or use the outermost-points method.')
        # An edge check alone misses two shells touching at one vertex.
        for link in links:
            if not link:continue
            visited=set();todo=[next(iter(link))]
            while todo:
                i=todo.pop()
                if i in visited:continue
                visited.add(i);todo.extend(link[i]-visited)
            if len(visited)!=len(link) or any(len(n)!=2 for n in link.values()):raise ValueError('Curved surface has a nonmanifold vertex. Adjust the neighbor limit.')
        new=[]
        for i,nbrs in enumerate(neighbors):
            if i%256==0:checkpoint()
            n=len(nbrs)
            if not n:new.append(v[i].tolist());continue
            beta=3/16 if n==3 else 3/(8*n)
            new.append(((1-n*beta)*v[i]+beta*v[sorted(nbrs)].sum(axis=0)).tolist())
        edge_index={}
        for edge_number,((a,b),(c,d)) in enumerate(sorted(edges.items())):
            if edge_number%256==0:checkpoint()
            edge_index[(a,b)]=len(new);new.append((3/8*(v[a]+v[b])+1/8*(v[c]+v[d])).tolist())
        refined=[]
        for a,b,c in f:
            ab=edge_index[tuple(sorted((a,b)))];bc=edge_index[tuple(sorted((b,c)))];ca=edge_index[tuple(sorted((c,a)))]
            refined.extend(([a,ab,ca],[b,bc,ab],[c,ca,bc],[ab,bc,ca]))
        v=np.array(new);f=refined
    result['control_halfspaces']=result.pop('halfspaces',[])
    result['control_tetrahedra']=result.pop('tetrahedra',[])
    result['vertices']=v.tolist();result['faces']=f
    result['area']=float(sum(np.linalg.norm(np.cross(v[b]-v[a],v[c]-v[a]))/2 for a,b,c in f))
    result['volume']=float(abs(sum(np.dot(v[a],np.cross(v[b],v[c]))/6 for a,b,c in f))) if model['volume'] is not None else None
    result['message']+=' Curved Loop surface approximation; smoothing rounds and shrinks the control mesh and may no longer enclose all source points. Area/volume refer to the exported tessellation; self-intersections are not tested.'
    return result


def material_text(color):
    rgb=[int(color[i:i+2],16)/255 for i in (1,3,5)]
    return 'newmtl atlas_surface\nKd '+' '.join(f'{x:.8f}' for x in rgb)+'\nKa 0 0 0\nd 1\nillum 1\n'
