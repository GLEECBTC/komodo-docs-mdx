#!/bin/bash

./gen_api_methods_table.py

cd js && npm ci
cd ../../
#node utils/js/get_file_author_data.js
node utils/js/validate_update_internal_links_userpass.js
node utils/js/file_presence_structure_checker.js
node utils/js/h1_presence_format_checker.js
node utils/js/validate_compact_table_data.js
node utils/js/ensure_changelog_update.js
#node utils/js/create_data_for_gpts.js
#node utils/js/create_search_index.js
