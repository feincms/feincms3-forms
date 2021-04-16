#!/bin/bash
set -ex

TAG="$1"
git commit -m "feincms3-forms $TAG"
git tag -m "feincms3-forms $TAG" "$TAG"
git push --all
git push --tags
rm -r dist
python3 setup.py sdist bdist_wheel
twine upload dist/*
