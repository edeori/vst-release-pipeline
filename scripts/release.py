"""Start a central build using the developer's existing gh login."""
import argparse
import subprocess
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('product')
parser.add_argument('--ref', default='main')
parser.add_argument('--publish', action='store_true')
args = parser.parse_args()
subprocess.run(['gh', 'workflow', 'run', 'release.yml', '--repo', 'edeori/vst-release-pipeline',
                '--ref', 'main', '-f', 'product=' + args.product, '-f', 'ref=' + args.ref,
                '-f', 'publish=' + str(args.publish).lower()], check=True)
print('Build requested: https://github.com/edeori/vst-release-pipeline/actions')
