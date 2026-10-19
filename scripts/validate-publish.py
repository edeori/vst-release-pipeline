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


def main():
    repository = os.environ['GITHUB_REPOSITORY']
    run_id = os.environ['BUILD_RUN_ID']
    if not re.fullmatch(r'[1-9][0-9]*', run_id):
        raise ValueError('Provide the numeric build run ID')
    def api(path):
        return json.loads(subprocess.check_output(['gh', 'api', f'repos/{repository}/{path}']))
    repo = api('')
    if os.environ['GITHUB_EVENT_NAME'] != 'workflow_dispatch' or os.environ['GITHUB_REF'] != 'refs/heads/' + repo['default_branch']:
        raise ValueError('Publish must be manually started from the default branch')
    workflow = api('actions/workflows/release.yml')
    run = api('actions/runs/' + run_id)
    sha = validate(run, repository, workflow['id'])
    with open(os.environ['GITHUB_OUTPUT'], 'a') as out:
        out.write(f'source_sha={sha}\n')
    print(f'Validated successful build {run_id} from {sha}')


if __name__ == '__main__':
    main()
