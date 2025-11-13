#!/bin/bash

set -e

MDX_BRANCH=$(git branch --show-current)
UI_BRANCH=test-ui
echo "UI branch: $UI_BRANCH"
echo "MDX branch: $MDX_BRANCH"

cd ../../komodo-docs-revamp-2023
git checkout dev
git pull
git branch -D $UI_BRANCH || true
git checkout -b $UI_BRANCH
cd utils
./update_mdx_branch.sh $MDX_BRANCH
cd ..
./update-content.sh
yarn build


