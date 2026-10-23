"""Lossless local capture adapter. Never connects to or mutates a database.

Callers supply fully loaded ORM rows from an authorized read. Capture records are
evidence, not publishable revisions or reconstructed historical deliveries.
"""
import base64
from copy import deepcopy
from hashlib import sha256
from urllib.parse import unquote_to_bytes

from sqlalchemy import inspect


def _columns(row):
    state=inspect(row)
    keys=[column.key for column in state.mapper.column_attrs]
    if set(keys) & (state.unloaded | state.expired_attributes):
        raise ValueError('Capture requires explicitly loaded columns; implicit database reads are forbidden')
    return {key:deepcopy(getattr(row,key)) for key in keys}


def capture_question(question, options, *, expected_option_ids):
    """Preserve scalars against independently extracted option-ID evidence.

    expected_option_ids must come from an unfiltered authorized extraction in the
    same database snapshot, not from the ORM relationship being checked.
    """
    record=_columns(question)
    state=inspect(question)
    if state.identity is None or 'options' in state.unloaded:
        raise ValueError('Capture requires a persisted question with explicitly loaded complete options')
    if type(record.get('id')) is not int or record['id']<1:
        raise ValueError('Persisted question identity required')
    rows=[_columns(option) for option in options]
    ids=[row.get('id') for row in rows]
    expected=list(expected_option_ids)
    if any(type(value) is not int or value<1 for value in expected) or len(expected)!=len(set(expected)):
        raise ValueError('Invalid independent option-ID evidence')
    if any(type(value) is not int or value<1 for value in ids) or len(ids)!=len(set(ids)):
        raise ValueError('Persisted distinct option identities required')
    if any(row.get('question_id')!=record['id'] for row in rows):
        raise ValueError('Option belongs to another question')
    related_ids={inspect(option).identity[0] for option in question.options if inspect(option).identity is not None}
    if set(ids)!=related_ids or len(related_ids)!=len(question.options):
        raise ValueError('Capture requires the complete loaded option set')
    if set(ids)!=set(expected):
        raise ValueError('Loaded options differ from independent option-ID evidence')
    rows.sort(key=lambda row:row['id'])
    refs=[]
    for kind,identity,reference in [('question',record['id'],record.get('question_image_url')),
                                   *[('option',r['id'],r.get('image_url')) for r in rows]]:
        if reference is None:
            continue
        asset={'owner_kind':kind,'owner_id':identity,'reference':reference,
               'content_sha256':None,'bytes_verified':False}
        if isinstance(reference,str) and reference.startswith('data:'):
            try:
                header,body=reference.split(',',1)
                raw=base64.b64decode(body,validate=True) if header.endswith(';base64') else unquote_to_bytes(body)
                asset.update(content_sha256=sha256(raw).hexdigest(),bytes_verified=True)
            except ValueError:
                pass
        refs.append(asset)
    return {'question':record,'options':rows,'asset_refs':refs,
            'capture_kind':'legacy_capture_at_migration','original_version_unknown':True,
            'publication_eligible':False}
