import os
import importlib.machinery
import importlib.util
from rdopkg.utils.git import git
from rdopkg import guess
import pytest

from unittest.mock import patch

import py.path

loader = importlib.machinery.SourceFileLoader('tarchanges', 'tar-changes')
spec = importlib.util.spec_from_loader(loader.name, loader)
tarchanges = importlib.util.module_from_spec(spec)
loader.exec_module(tarchanges)


TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
FIXTURES_DIR = os.path.join(TESTS_DIR, 'fixtures')


def test_clear_old_changes_sources(tmpdir, monkeypatch):
    # Copy our "sources" fixture file to a tmpdir.
    fixtures_dir = py.path.local(FIXTURES_DIR)
    fixtures_dir.join('sources').copy(tmpdir)
    monkeypatch.chdir(tmpdir)
    # Test clear_old_changes_sources().
    tarchanges.clear_old_changes_sources()
    sources = tmpdir.join('sources')
    expected = '3a393d427d5b16c33cf24da91244cc7a  ceph-12.2.8.tar.gz\n'
    assert sources.read() == expected


@pytest.fixture
def distgitdir(tmpdir):
    with tmpdir.as_cwd():
        git('init')
        tmpdir.join('contents.txt').write('initial contents')
        git('add', '-f', '.')

        git('commit', '-m', 'Initial import', isolated=True, print_stderr=True)
        tmpdir.join('contents.txt').write('second contents')
        git('commit', '-a', '-m' 'second commit')
    return tmpdir


def test_commit_distgit_amend(distgitdir):
    suffix = 'GitLab-User: developer@example.com'
    rng = 'HEAD~..HEAD'
    with distgitdir.as_cwd():
        tarchanges.commit_distgit_amend(suffix)
        message = git('log', '--format=%s%n%n%b', rng, log_cmd=False)
    expected = """\
second commit

GitLab-User: developer@example.com"""
    assert message == expected

@patch('rdopkg.guess.new_sources', autospec=True, return_value=True)
@patch.object(tarchanges, 'run')
@patch.object(tarchanges, 'clear_old_changes_sources')
def test_upload_source(delete_sources, mocked_run, mocked_sources):
    """
    See if the `[fedpkg|rhpkg] update` command gets called if both are true:
    1. guess.new_sources() returns True
    2. the --no-new-sources flag was not passed
    """

    # flag was not detected by argparse
    tarchanges.upload_source(guess.osdist(), 'test.tar', True)
    mocked_run.assert_called_once()

    # flag was detected by argparse
    tarchanges.upload_source(guess.osdist(), 'test.tar', False)
    mocked_run.assert_called_once() # run() was not called
