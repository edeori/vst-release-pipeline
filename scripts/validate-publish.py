"""Reject unrelated, unfinished or unsuccessful builds before downloading installers."""
import json
import os
import re
import subprocess


def validate(run, repository, workflow_id):
    if run.get('repository', {}).get('full_name', '').lower() != repository.lower():
        raise ValueError('Build belongs to a different repository')
    if run.get('workflow_id') != workflow_id:
        raise ValueError('Only the release.yml build workflow can be published')
    if run.get('status') != 'completed' or run.get('conclusion') != 'success':
        raise ValueError('Build must be completed successfully')
    if run.get('event') not in ('workflow_dispatch', 'push'):
        raise ValueError('Pull request builds cannot be published')
    if not re.fullmatch(r'[0-9a-f]{40}', run.get('head_sha', '')):
        raise ValueError('Missing source commit')
    return run['head_sha']


def select_latest(api, workflow_id, branch):
    from urllib.parse import urlencode
    page = 1
    while True:
        query = urlencode({'branch': branch, 'status': 'success', 'per_page': 100, 'page': page})
        runs = api(f'actions/workflows/{workflow_id}/runs?{query}')['workflow_runs']
        eligible = [run for run in runs if run.get('event') in ('workflow_dispatch', 'push')
                    and run.get('head_branch') == branch and run.get('status') == 'completed'
                    and run.get('conclusion') == 'success']
        if eligible:
            # Creation order, not completion time: rerunning an old build must not
            # silently replace a newer source build as the latest release candidate.
            return str(max(eligible, key=lambda r: (r['created_at'], r['id']))['id'])
        if len(runs) < 100:
            raise ValueError('No successful build exists on the default branch')
        page += 1


def main():
    repository = os.environ['GITHUB_REPOSITORY']
    run_id = os.environ.get('BUILD_RUN_ID', '').strip()
    selection = os.environ.get('BUILD_SELECTION', 'specific')
    if selection not in ('latest', 'specific'):
        raise ValueError('Unknown build selection')
    if selection == 'specific' and not re.fullmatch(r'[1-9][0-9]*', run_id):
        raise ValueError('Provide the numeric build run ID')
    if selection == 'latest' and run_id:
        raise ValueError('Leave build_run_id empty when selecting the latest build')
    def api(path):
        return json.loads(subprocess.check_output(['gh', 'api', f'repos/{repository}/{path}'.rstrip('/')]))
    repo = api('')
    if os.environ['GITHUB_EVENT_NAME'] != 'workflow_dispatch' or os.environ['GITHUB_REF'] != 'refs/heads/' + repo['default_branch']:
        raise ValueError('Publish must be manually started from the default branch')
    workflow = api('actions/workflows/release.yml')
    if selection == 'latest':
        run_id = select_latest(api, workflow['id'], repo['default_branch'])
    run = api('actions/runs/' + run_id)
    sha = validate(run, repository, workflow['id'])
    with open(os.environ['GITHUB_OUTPUT'], 'a') as out:
        out.write(f'source_sha={sha}\nrun_id={run_id}\n')
    print(f'Validated successful build {run_id} from {sha}')
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'], 'a') as summary:
            summary.write(f'Selected build: https://github.com/{repository}/actions/runs/{run_id}\n\nSource commit: `{sha}`\n')


if __name__ == '__main__':
    main()
