import copy
import sqlite3

import pytest

from app.services.revision_ledger import Ledger


@pytest.fixture
def ledger(tmp_path):
    value = Ledger(tmp_path / 'editorial.sqlite')
    yield value
    value.close()


def payload():
    return dict(stem='What is 2+2?', options=[dict(id=str(i), position=i, text=str(i+2), asset_id=None) for i in range(1,5)],
                answer_option_id='2', explanation='Two pairs make four.', difficulty=1, topic_id=1,
                taxonomy_version='draft-1', provenance=['original-fixture'], assets=[])


def approve(ledger, rid):
    ledger.review(rid, reviewer='independent-editor', evidence=dict(answer_verified=True, all_options_checked=True,
        instruction_reviewed=True, visual_reviewed=True, reference='independent-fixture-calculation'))


def initial(ledger):
    rid = ledger.candidate(42, payload(), author='author', reason='Original fixture')
    approve(ledger, rid)
    pid = ledger.publish(rid, actor='editor', expected_publication_id=None)
    return rid, pid


BLUEPRINT = dict(version='fixture-v1', scoring={'correct':2, 'wrong':-0.5}, timing={'minutes':60})


def test_correction_preserves_pinned_content_and_stored_result(ledger):
    rid, pid = initial(ledger)
    ledger.pin('practice:1', 42, revision_id=rid, blueprint=BLUEPRINT, legacy_result={'score':2})
    next_id = ledger.patch(rid, {'explanation':'Add two and two to obtain four.'}, author='author', reason='Clearer teaching')
    approve(ledger, next_id)
    ledger.publish(next_id, actor='editor', expected_publication_id=pid)
    assert ledger.revision(next_id)['answer_version'] == ledger.revision(rid)['answer_version']
    assert ledger.history('practice:1', 42)['revision']['payload']['explanation'] == payload()['explanation']
    assert ledger.history('practice:1', 42)['stored_result'] == {'score':2}
    assert ledger.revision(next_id)['payload']['topic_id'] == 1


def test_answer_change_versions_key_without_rescoring(ledger):
    rid, _ = initial(ledger)
    next_id = ledger.patch(rid, {'answer_option_id':'3'}, author='author', reason='Candidate correction')
    assert ledger.revision(next_id)['answer_version'] != ledger.revision(rid)['answer_version']
    assert ledger.head(42)['revision_id'] == rid


def test_independent_review_and_stale_editors(ledger):
    rid, pid = initial(ledger)
    a = ledger.patch(rid, {'explanation':'First explanation'}, author='author', reason='A')
    b = ledger.patch(rid, {'explanation':'Second explanation'}, author='author', reason='B')
    with pytest.raises(ValueError, match='Unreviewed'):
        ledger.publish(a, actor='editor', expected_publication_id=pid)
    with pytest.raises(ValueError, match='Independent'):
        ledger.review(a, reviewer='author', evidence={})
    approve(ledger, a); approve(ledger, b)
    ledger.publish(a, actor='editor', expected_publication_id=pid)
    with pytest.raises(ValueError, match='Stale'):
        ledger.publish(b, actor='editor', expected_publication_id=pid)


@pytest.mark.parametrize('table', ['revisions','reviews','publications','pins'])
@pytest.mark.parametrize('operation', ['UPDATE','DELETE'])
def test_raw_sql_cannot_mutate_evidence(ledger, table, operation):
    rid, _ = initial(ledger)
    ledger.pin('mock:1',42,revision_id=rid,blueprint=BLUEPRINT)
    column = {'revisions':'reason','reviews':'reviewer','publications':'actor','pins':'attempt_key'}[table]
    sql = f"UPDATE {table} SET {column}='changed'" if operation == 'UPDATE' else f'DELETE FROM {table}'
    with pytest.raises(sqlite3.IntegrityError, match='immutable'):
        ledger.db.execute(sql)


def test_legacy_uncertainty_is_not_fabricated(ledger):
    rid, _ = initial(ledger)
    with pytest.raises(ValueError, match='unknown'):
        ledger.pin('old:1',42,revision_id=rid,blueprint=BLUEPRINT,historical=True)
    ledger.pin('old:1',42,revision_id=None,blueprint=BLUEPRINT,historical=True,legacy_result={'score':123.5,'status':'submitted'})
    old = ledger.history('old:1',42)
    assert old['original_version_unknown'] == 1 and old['revision'] is None
    assert old['stored_result']['score'] == 123.5


@pytest.mark.parametrize('change', [{'topic_id':None},{'answer_option_id':'missing'},{'difficulty':True},{'assets':[{'id':'x','sha256':'bad','alt':'figure'}]}])
def test_invalid_candidate_is_withheld(ledger,change):
    with pytest.raises(ValueError):
        ledger.candidate(42,{**payload(),**change},author='author',reason='fixture')


def test_duplicate_and_changed_option_content(ledger):
    rid, _ = initial(ledger)
    value=copy.deepcopy(payload())
    value['options'][0]['text']='Different value'
    changed=ledger.patch(rid,{'options':value['options']},author='author',reason='Changed assessed option')
    assert ledger.revision(changed)['answer_version'] != ledger.revision(rid)['answer_version']
    value['options'][0]['text']=value['options'][1]['text']
    with pytest.raises(ValueError,match='Duplicate'):
        ledger.candidate(42,value,author='author',reason='Duplicate')


def test_reopen_preserves_history(tmp_path):
    path=tmp_path/'editorial.sqlite'
    first=Ledger(path)
    rid,_=initial(first)
    first.pin('mock:77',42,revision_id=rid,blueprint=BLUEPRINT)
    first.close()
    second=Ledger(path)
    assert second.history('mock:77',42)['revision']['id']==rid
    second.close()


@pytest.mark.parametrize('table',['revisions','reviews','publications','pins'])
def test_replace_cannot_bypass_immutability(ledger,table):
    rid,_=initial(ledger)
    ledger.pin('mock:1',42,revision_id=rid,blueprint=BLUEPRINT)
    ledger.db.execute('PRAGMA recursive_triggers=OFF')
    with pytest.raises(sqlite3.IntegrityError,match='immutable'):
        ledger.db.execute(f'INSERT OR REPLACE INTO {table} SELECT * FROM {table}')


def test_changed_asset_bytes_version_assessed_key(ledger):
    value=payload()
    value['assets']=[{'id':'figure','sha256':'a'*64,'alt':'A geometric figure'}]
    value['options'][0]['asset_id']='figure'
    rid=ledger.candidate(42,value,author='author',reason='Visual fixture')
    changed=ledger.patch(rid,{'assets':[{'id':'figure','sha256':'b'*64,'alt':'A geometric figure'}]},author='author',reason='Correct rendering')
    assert ledger.revision(rid)['answer_version'] != ledger.revision(changed)['answer_version']


def test_pin_holds_write_lock_during_head_check(tmp_path,monkeypatch):
    path=tmp_path/'concurrent.sqlite'
    first=Ledger(path)
    rid,_=initial(first)
    second=Ledger(path)
    second.db.execute('PRAGMA busy_timeout=1')
    original=first.head
    def checked(qid):
        with pytest.raises(sqlite3.OperationalError,match='locked'):
            second.db.execute('BEGIN IMMEDIATE')
        return original(qid)
    monkeypatch.setattr(first,'head',checked)
    first.pin('new:1',42,revision_id=rid,blueprint=BLUEPRINT)
    first.close();second.close()


@pytest.mark.parametrize('qid,historical,blueprint',[(0,True,BLUEPRINT),(42,2,BLUEPRINT),(42,True,dict(version='x',scoring='bad',timing='bad'))])
def test_invalid_pin_metadata_rejected(ledger,qid,historical,blueprint):
    with pytest.raises(ValueError):
        ledger.pin('old:1',qid,revision_id=None,blueprint=blueprint,historical=historical)


def test_unique_index_replace_cannot_delete_publication(ledger):
    rid,pid=initial(ledger)
    ledger.db.execute('PRAGMA recursive_triggers=OFF')
    with pytest.raises(sqlite3.IntegrityError,match='immutable'):
        ledger.db.execute("INSERT OR REPLACE INTO publications VALUES ('replacement',42,?,NULL,'other','now')",(rid,))
    assert ledger.head(42)['id']==pid


@pytest.mark.parametrize('table',['revisions','reviews','publications','pins'])
def test_no_rowid_replacement_path(ledger,table):
    with pytest.raises(sqlite3.OperationalError,match='no such column'):
        ledger.db.execute(f'SELECT rowid FROM {table}')


def test_older_schema_rejected_without_rewriting_evidence(tmp_path):
    path=tmp_path/'old.sqlite'
    with sqlite3.connect(path) as db:
        db.execute('CREATE TABLE revisions (id TEXT PRIMARY KEY, payload TEXT)')
        db.execute("INSERT INTO revisions VALUES ('old','preserve exactly')")
    with pytest.raises(ValueError,match='older ledger'):
        Ledger(path)
    with sqlite3.connect(path) as db:
        assert db.execute('SELECT * FROM revisions').fetchall()==[('old','preserve exactly')]


def test_concurrent_publish_has_one_winner(tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    path=tmp_path/'race.sqlite'
    ledger=Ledger(path)
    rid,pid=initial(ledger)
    candidates=[ledger.patch(rid,{'explanation':f'Explanation {i}'},author='author',reason='Concurrent edit') for i in range(2)]
    for candidate in candidates:approve(ledger,candidate)
    ledger.close()
    barrier=Barrier(2)
    def worker(candidate):
        local=Ledger(path)
        try:
            barrier.wait(timeout=5)
            try:
                local.publish(candidate,actor='editor',expected_publication_id=pid)
                return 'published'
            except ValueError as error:
                assert 'Stale' in str(error)
                return 'stale'
        finally:local.close()
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(worker,candidates))==['published','stale']
