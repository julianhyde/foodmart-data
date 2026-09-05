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
# foodmart-data HOWTO

Here's some miscellaneous documentation about using and developing
foodmart-data.

# Build

Build and test everything, Go and Rust:

```bash
fullMake
```

Or by hand:

```bash
./tools/schema.py
go vet ./... && golangci-lint run ./... && go test ./...
cargo clippy --all-targets -- -D warnings && cargo test
```

# Add or change a table

`schema.go` and `src/schema.rs` are generated. Edit the `SCHEMA` table
in [tools/schema.py](tools/schema.py), then regenerate:

```bash
./tools/schema.py
```

Generating checks that every column matches the header row of its CSV
file, and that there is no CSV file that `SCHEMA` does not describe, so
it fails rather than emitting a schema that disagrees with the data.

# Release

Releasing publishes two artifacts from one tag: the Go module, for
which pushing the tag is enough, and the crate, which is uploaded to
[crates.io](https://crates.io/crates/foodmart-data). They fail in
different ways, so read
[what cannot be undone](#what-cannot-be-undone) before you start.

Check that the sandbox is clean, and that the generated files are up to
date:

```bash
git clean -nx
./tools/schema.py
git diff --exit-code
```

Run the full build, on the latest stable toolchains and on the minimum
versions in
[.github/workflows/main.yml](.github/workflows/main.yml):

```bash
fullMake --clean
```

Update the [release history](CHANGELOG.md),
the `version` in [Cargo.toml](Cargo.toml),
the two version numbers in [README](README.md)
(the `foodmart-data = "x.y.z"` dependency and the `go get` command),
and the copyright date in [NOTICE](NOTICE).

Check that the crate contains everything it should, and nothing it
should not. `cargo package` builds the crate from the packaged tarball
alone, so it catches a file missing from the `include` list in
`Cargo.toml`; `cargo publish --dry-run` does the same and also
validates the metadata that crates.io will see:

```bash
cargo package --list
cargo package
ls -l target/package/foodmart-data-*.crate
cargo publish --dry-run
```

(`cargo publish --dry-run` does not leave the `.crate` file behind, so
run `cargo package` if you want to look at it.)

The `.crate` must be under 10MB, which is the crates.io limit. It is
currently about 3.7MB; if it ever approaches the limit, ship the CSV
files compressed rather than asking for the limit to be raised.

Check what the Go module proxy will see. It builds the module from the
tag using `git archive`, so a file that is untracked, or ignored, or in
a git submodule, will not be there &mdash; and `go:embed` fails to
compile if the CSV files are missing:

```bash
git archive HEAD | tar t | grep -c '^csv/.*\.csv$'   # expect 26
```

Commit, then tag and push. The tag must be `vx.y.z`, with the `v` and
all three parts; the Go module proxy ignores any other form:

```bash
git commit -m '[release] Release x.y.z'
git tag vx.y.z
git push origin main vx.y.z
```

Publish the crate:

```bash
cargo publish
```

Ask the Go module proxy to fetch the tag, and check that a project that
depends on it builds:

```bash
cd $(mktemp -d)
go mod init tmp
GOPROXY=proxy.golang.org go get github.com/hydromatic/foodmart-data@vx.y.z
cat > main.go <<'EOF'
package main

import (
	"fmt"

	foodmart "github.com/hydromatic/foodmart-data"
)

func main() {
	table, _ := foodmart.Find("days")
	rows, err := table.ReadAll()
	fmt.Println(len(rows), err)
}
EOF
go run .    # expect "7 <nil>"
```

Check that [docs.rs](https://docs.rs/foodmart-data) and
[pkg.go.dev](https://pkg.go.dev/github.com/hydromatic/foodmart-data)
have picked up the new version.

Update the [release history](CHANGELOG.md) and the version in
[README](README.md) for the next development version.

## What cannot be undone

A release cannot be withdrawn from either registry, so the checks above
are worth doing in order.

* **crates.io.** A published version can only be
  [yanked](https://doc.rust-lang.org/cargo/commands/cargo-yank.html),
  which stops new projects resolving to it but leaves it downloadable
  forever. The version number can never be used again.
* **The Go module proxy.** Once anyone fetches a version, its hash is
  recorded permanently in the
  [checksum database](https://sum.golang.org/). Moving or deleting the
  tag afterwards does not change what `go get` returns; it only makes
  the tag disagree with what everyone downloads. A broken release can
  only be superseded by a higher version.

The Go side is the riskier of the two, because nothing is uploaded and
so nothing is validated until a user builds against the tag. That is
what the `git archive` check above is for.

<!-- End HOWTO.md -->
