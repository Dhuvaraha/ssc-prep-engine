"""Independent geometric checks; rendered subject review remains a separate gate."""
from fractions import Fraction as F
from app.services.pilot_curriculum import load_unit


def reflected(point,line):
    a,b=line
    dx,dy=F(b.x-a.x),F(b.y-a.y)
    t=(F(point.x-a.x)*dx+F(point.y-a.y)*dy)/(dx*dx+dy*dy)
    return (2*(F(a.x)+t*dx)-F(point.x),2*(F(a.y)+t*dy)-F(point.y))


def coordinates(scene):
    return [[(F(p.x),F(p.y)) for p in polygon] for polygon in scene.polygons],[(F(p.x),F(p.y)) for p in scene.dots]


def test_all_authored_reflection_keys_using_line_projection():
    for oid in ('MIR-1','MIR-4','MIR-5'):
        for checks in load_unit(oid).checks.values():
            for q in checks:
                figure=q.figure;assert figure is not None
                accepted=[]
                for candidate in figure.options:
                    if oid=='MIR-1':
                        n=len(figure.stem.polygons)//2;m=len(figure.stem.dots)//2
                        original_polys=figure.stem.polygons[:n];original_dots=figure.stem.dots[:m]
                        target=([[ (F(p.x),F(p.y)) for p in poly] for poly in figure.stem.polygons[n:]],
                                [(F(p.x),F(p.y)) for p in figure.stem.dots[m:]])
                    else:
                        original_polys=figure.stem.polygons;original_dots=figure.stem.dots
                        target=coordinates(candidate)
                    line=candidate.lines[0]
                    mapped=([[reflected(p,line) for p in poly] for poly in original_polys],
                            [reflected(p,line) for p in original_dots])
                    accepted.append(mapped==target)
                assert accepted==[i==q.answer-1 for i in range(4)],q.id


def test_image_distance_is_half_original_to_image_separation():
    for checks in load_unit('MIR-2').checks.values():
        for q in checks:
            point=q.diagram.polygons[0][0];image=reflected(point,q.diagram.lines[0])
            distance=F(q.options[q.answer-1])
            assert (F(point.x)-image[0])**2+(F(point.y)-image[1])**2==4*distance**2


def test_transformation_classification_matches_all_vertices_and_dots():
    rules=[lambda x,y:(-x,y),lambda x,y:(x,-y),lambda x,y:(-x,-y),lambda x,y:(x+90,y-20)]
    for checks in load_unit('MIR-3').checks.values():
        for q in checks:
            scene=q.diagram
            source=scene.polygons[0]+scene.dots[:1]
            target=scene.polygons[1]+scene.dots[1:]
            valid=[all(rule(p.x,p.y)==(t.x,t.y) for p,t in zip(source,target,strict=True)) for rule in rules]
            assert valid==[i==q.answer-1 for i in range(4)],q.id
