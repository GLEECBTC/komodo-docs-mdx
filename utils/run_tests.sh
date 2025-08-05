#!/bin/bash

cd "$(dirname "$0")"

npm ci --prefix js
#node js/get_file_author_data.js
node js/validate_update_internal_links_userpass.js
node js/file_presence_structure_checker.js
node js/h1_presence_format_checker.js
node js/ensure_changelog_update.js
node js/findMissingRedirects.js
node js/createRedirectMap.js
#node js/create_data_for_gpts.js
#node js/create_search_index.js
