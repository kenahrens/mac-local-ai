import contextlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import sandbox


class FailedSetupTests(unittest.TestCase):
    def setUp(self):
        scratch = tempfile.TemporaryDirectory()
        self.addCleanup(scratch.cleanup)
        self.root = Path(scratch.name)
        self.config = self.root / 'config.yaml'
        self.config.write_text('test fixture\n')
        self.guests = set()
        self.removals = []
        self.failure = ValueError('source download failed')
        self.stderr = io.StringIO()
        self.stdout = io.StringIO()
        self.patch(sandbox, 'RUNS', self.root / 'runs')
        self.patch(sandbox, 'SPEEDSCALE_CONFIG', self.config)
        self.patch(sandbox, 'credential_env')
        self.patch(sandbox, 'ensure_login')
        self.patch(sandbox, 'run', side_effect=self.guest_run)
        self.output = self.patch(sandbox, 'output', side_effect=self.output_for)
        self.patch(sandbox.subprocess, 'run', side_effect=self.subprocess_run)
        self.seed = self.patch(sandbox, 'seed_mock_lab', side_effect=self.failure)
        self.patch(sandbox, 'configure')
        self.patch(sandbox, 'ensure_agents')
        self.patch(sandbox.shutil, 'which', return_value='/fixture/bin')
        self.enter(contextlib.redirect_stderr(self.stderr))
        self.enter(contextlib.redirect_stdout(self.stdout))

    def patch(self, target, name, *args, **kwargs):
        return self.enter(patch.object(target, name, *args, **kwargs))

    def enter(self, manager):
        result = manager.__enter__()
        self.addCleanup(manager.__exit__, None, None, None)
        return result

    def guest_run(self, *args, **kwargs):
        if args[:2] == ('sbx', 'create'):
            self.guests.add(args[args.index('--name') + 1])
        elif args[:2] == ('sbx', 'rm'):
            self.guests.remove(args[-1])
        return subprocess.CompletedProcess(args, 0)

    def output_for(self, *args):
        if args[:3] == ('sbx', 'template', 'ls'):
            return json.dumps({'images': [{'repository': 'speedscale-ai-sandbox', 'tag': 'node-v2'}]})
        return 'sha256:fixture'

    def subprocess_run(self, args, **kwargs):
        if args[:2] == ['sbx', 'rm']:
            self.assertIn('--force', args)
            self.assertEqual(self.state()['status'], 'failed')
            self.removals.append(args)
            self.guests.remove(args[-1])
        return subprocess.CompletedProcess(args, 0, stdout='', stderr='')

    def state(self):
        states = list(sandbox.RUNS.glob('*/session.json'))
        self.assertEqual(len(states), 1)
        return json.loads(states[0].read_text())

    def assert_failed(self, expected=None):
        with self.assertRaises(type(expected or self.failure)) as caught:
            sandbox.new('node', no_open=True)
        self.assertIs(caught.exception, expected or self.failure)
        self.assertEqual(self.state()['status'], 'failed')
        with self.assertRaisesRegex(ValueError, 'No sandbox yet'):
            sandbox.take_path('latest')
        self.assertFalse(self.guests)
        self.assertEqual(len(self.removals), 1)

    def test_download_failure_removes_guest_without_confirmation(self):
        self.assert_failed()

    def test_image_inspection_failure_after_creation_removes_guest(self):
        self.output.side_effect = lambda *args: self.output_for(*args) if args[0] != 'docker' else self.raise_failure()
        self.assert_failed()
        self.seed.assert_not_called()

    def raise_failure(self):
        raise self.failure

    def test_partial_creation_failure_removes_guest(self):
        def create_then_fail(*args, **kwargs):
            self.guest_run(*args, **kwargs)
            raise self.failure
        self.patch(sandbox, 'run', side_effect=create_then_fail)
        self.assert_failed()

    def test_metadata_write_failure_after_creation_removes_guest(self):
        self.failure = OSError('metadata disk full')
        real_save = sandbox.save
        def save(path, data):
            if 'mock_lab_commit' in data and data['status'] != 'failed':
                raise self.failure
            real_save(path, data)
        self.patch(sandbox, 'save', side_effect=save)
        self.seed.side_effect = None
        self.seed.return_value = 'fixture-commit'
        self.assert_failed()

    def test_failed_status_write_error_still_removes_guest(self):
        real_save = sandbox.save
        def save(path, data):
            if data['status'] == 'failed':
                raise OSError('metadata disk full')
            real_save(path, data)
        self.patch(sandbox, 'save', side_effect=save)
        def cleanup(args, **kwargs):
            if args[:2] == ['sbx', 'rm']:
                self.assertIn('--force', args)
                self.guests.remove(args[-1])
            return subprocess.CompletedProcess(args, 0, stdout='', stderr='')
        self.patch(sandbox.subprocess, 'run', side_effect=cleanup)
        with self.assertRaises(ValueError) as caught:
            sandbox.new('node', no_open=True)
        self.assertIs(caught.exception, self.failure)
        self.assertFalse(self.guests)
        self.assertIn('Could not save failed session', self.stderr.getvalue())

    def test_interrupt_removes_guest_and_preserves_interrupt(self):
        interruption = KeyboardInterrupt()
        self.seed.side_effect = interruption
        self.assert_failed(interruption)

    def test_failed_cleanup_can_be_retried_through_remove_command(self):
        self.patch(sandbox.subprocess, 'run', side_effect=lambda args, **kwargs:
                   subprocess.CompletedProcess(args, 1, stdout='', stderr='removal unavailable')
                   if args[:2] == ['sbx', 'rm'] else self.subprocess_run(args, **kwargs))
        with self.assertRaises(ValueError) as caught:
            sandbox.new('node', no_open=True)
        self.assertIs(caught.exception, self.failure)
        state = self.state()
        self.assertEqual(state['status'], 'failed')
        self.assertEqual(self.guests, {state['sandbox']})
        self.assertIn('removal unavailable', self.stderr.getvalue())
        self.assertIn(f"ai-sandbox remove {state['id']}", self.stderr.getvalue())
        with self.assertRaisesRegex(ValueError, 'Setup for this sandbox failed'):
            sandbox.session(state['id'])
        with patch.object(sys, 'argv', ['ai-sandbox', 'remove', state['id']]):
            sandbox.main()
        self.assertFalse(self.guests)
        self.assertEqual(self.state()['status'], 'removed')
        self.assertTrue((sandbox.RUNS / state['id'] / 'recordings').is_dir())

    def test_successful_setup_keeps_guest_and_ready_metadata(self):
        self.seed.side_effect = None
        self.seed.return_value = 'fixture-commit'
        identifier = sandbox.new('node', no_open=True)
        state = self.state()
        self.assertEqual(state['status'], 'ready')
        self.assertTrue(state['clean_start_verified'])
        self.assertEqual(self.guests, {state['sandbox']})
        self.assertFalse(self.removals)
        self.assertEqual(sandbox.take_path('latest').name, identifier)


if __name__ == '__main__':
    unittest.main()
