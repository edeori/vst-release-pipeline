"""Only centrally registered repositories may access release credentials."""
import json
import os
import re
from pathlib import Path


def resolve(product, config):
    if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', product):
        raise ValueError('Invalid product ID')
    repository = config[product]['repository']
    if not re.fullmatch(r'edeori/[A-Za-z0-9_.-]+', repository):
        raise ValueError('Only registered edeori repositories are allowed')
    return repository


if __name__ == '__main__':
    repository = resolve(os.environ['PRODUCT_ID'], json.loads(Path(__file__).resolve().parents[1].joinpath('products.json').read_text()))
    with open(os.environ['GITHUB_OUTPUT'], 'a') as output:
        output.write('repository=' + repository + '\n')
