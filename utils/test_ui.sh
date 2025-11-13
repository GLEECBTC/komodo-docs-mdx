#!/bin/bash

set -e

MDX_BRANCH=$(git branch --show-current)
UI_BRANCH=test-ui
echo "UI branch: $UI_BRANCH"
echo "MDX branch: $MDX_BRANCH"

cd ../../komodo-docs-revamp-2023
git checkout dev
git pull

# Uncomment this to delete the branch
# Leave it uncommented to keep local changes to the branch
git branch -D $UI_BRANCH || true

git checkout -b $UI_BRANCH || true
cd utils
./update_mdx_branch.sh $MDX_BRANCH
cd ..
./update-content.sh
yarn build


