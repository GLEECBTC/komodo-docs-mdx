#!/bin/bash

./gen_api_methods_table.py || exit 1

cd js && npm ci
cd ../../
#node utils/js/get_file_author_data.js
node utils/js/validate_update_internal_links_userpass.js || exit 1
node utils/js/file_presence_structure_checker.js || exit 1
node utils/js/h1_presence_format_checker.js || exit 1
node utils/js/validate_compact_table_data.js || exit 1
node utils/js/ensure_changelog_update.js || exit 1
#node utils/js/create_data_for_gpts.js
#node utils/js/create_search_index.js
