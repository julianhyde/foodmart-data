<!--
{% comment %}
Licensed to Julian Hyde under one or more contributor license
agreements.  See the NOTICE file distributed with this work
for additional information regarding copyright ownership.
Julian Hyde licenses this file to you under the Apache
License, Version 2.0 (the "License"); you may not use this
file except in compliance with the License.  You may obtain a
copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on an
"AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied.  See the License for the specific
language governing permissions and limitations under the
License.
{% endcomment %}
-->
# Foodmart data release history and change log

For a full list of releases, see
<a href="https://github.com/hydromatic/foodmart-data/releases">GitHub</a>.

## <a href="https://github.com/hydromatic/foodmart-data/releases/tag/v0.6.0">0.6.0</a> / 2026-09-04

First release. It provides the Foodmart data set as a Go module and a
Rust crate, both of which embed the data as CSV files and have no
dependencies.

The version number matches
[foodmart-data-hsqldb](https://github.com/julianhyde/foodmart-data-hsqldb)
0.6, from which the CSV files are taken.

It requires Rust 1.71 or higher, and Go 1.22 or higher.

* Add a Go module, `github.com/hydromatic/foodmart-data`
* Add a Rust crate, `foodmart-data`
* Generate `schema.go` and `src/schema.rs` from the schema in
  `tools/schema.py`

<!-- End CHANGELOG.md -->
