"""Offline coverage of an existing private proposal, never grant generation."""
import base64
from collections import Counter
from hashlib import sha256
from urllib.parse import unquote_to_bytes
import xml.etree.ElementTree as ET


def coverage(inventory, topology, proposal):
    sources = {s['id']:s for s in proposal['sources']}
    bindings = {b['resource_id']:b['source_id'] for b in proposal['bindings'] if b['resource_kind']=='question'}
    expected = {qid for g in topology['question_groups'] for qid in g['ids']}
    if len(bindings) != len(proposal['bindings']) or set(bindings) != expected or not set(bindings.values()) <= set(sources):
        raise ValueError('Question mapping is incomplete or ambiguous')
    originals = {qid for qid,sid in bindings.items() if sources[sid].get('authorship_status')=='repository_generated_content_match'}
    pools=[]
    for group in topology['question_groups']:
        pools.append({k:group[k] for k in ('exam_id','subject_id','topic_id','difficulty')} | {
            'total':len(group['ids']), 'repository_content_matches':len(set(group['ids']) & originals),
            'rights_and_access_approved':False})
    assets=[]
    for item in inventory['assets']:
        raw=item['asset_url']
        result={'usage':item['usage'], 'question_ids':item['question_ids'],
                'asset_reference_digest':sha256(raw.encode()).hexdigest(),
                'source_ids':sorted({bindings[qid] for qid in item['question_ids']}),
                'visual_review_complete':False, 'rights_approved':False}
        try:
            header,body=raw.split(',',1)
            if not header.startswith('data:image/svg+xml'):
                raise ValueError('Unsupported asset encoding')
            data=base64.b64decode(body,validate=True) if header.endswith(';base64') else unquote_to_bytes(body)
            if len(data)>2_000_000 or b'<!DOCTYPE' in data.upper() or b'<!ENTITY' in data.upper():
                raise ValueError('Unsafe XML')
            root=ET.fromstring(data)
            if root.tag.split('}')[-1]!='svg':
                raise ValueError('Not SVG')
            unsafe=False
            for element in root.iter():
                if element.tag.split('}')[-1].lower() in {'script','foreignobject','iframe','style','animate','set'}:
                    unsafe=True
                for key,value in element.attrib.items():
                    key=key.split('}')[-1].lower()
                    if key.startswith('on') or key in {'href','src','style'} or 'url(' in value.lower():
                        unsafe=True
            result.update(content_sha256=sha256(data).hexdigest(), decoded_bytes=len(data),
                          static_svg_screen_passed=not unsafe)
        except (ValueError,ET.ParseError):
            result.update(content_sha256=None, static_svg_screen_passed=False)
        assets.append(result)
    resources=[dict(resource_kind=r['kind'],resource_id=r['id'],topic_id=r['topic_id'],
                    contributor_status='unresolved', reason='No exact full-content contributor evidence in cached inventory')
               for r in inventory['resources']]
    return {'executable':False,'proposal_source_groups':len(sources),'question_bindings':len(bindings),
            'repository_content_matches':len(originals),'topic_difficulty_pools':pools,
            'resource_mapping_gaps':resources,'assets':assets,
            'observed_course_candidates':proposal['courses'],
            'active_course_grants':sum(c.get('active') is True for c in proposal['courses']),
            'active_source_grants':sum(g.get('active') is True for g in proposal['grants']),
            'summary':{'resource_gaps':dict(Counter(r['kind'] for r in inventory['resources'])),
                       'asset_groups':len(assets),'static_svg_screen_passed':sum(a['static_svg_screen_passed'] for a in assets),
                       'visual_approvals':0},'production_ready':False}
