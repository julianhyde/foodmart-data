// Licensed to Julian Hyde under one or more contributor license
// agreements.  See the NOTICE file distributed with this work for
// additional information regarding copyright ownership. Julian Hyde
// licenses this file to you under the Apache License, Version 2.0 (the
// "License"); you may not use this file except in compliance with the
// License.  You may obtain a copy of the License at
//
// http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

//nolint:testpackage // white-box: tests the unexported Column.value
package foodmart

import (
	"errors"
	"io"
	"io/fs"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

// Kick the tires.
func TestTableNames(t *testing.T) {
	names := TableNames()
	if got, want := len(names), 26; got != want {
		t.Fatalf("got %d tables, want %d", got, want)
	}
	if got, want := names[0], "account"; got != want {
		t.Errorf("got %q, want %q", got, want)
	}
	if got, want := names[25], "warehouse_class"; got != want {
		t.Errorf("got %q, want %q", got, want)
	}
	for _, name := range names {
		if len(name) > 4 && name[:4] == "agg_" {
			t.Errorf("aggregate table %q should not be present", name)
		}
	}
}

func TestFind(t *testing.T) {
	table, ok := Find("customer")
	if !ok {
		t.Fatal("customer not found")
	}
	if got, want := len(table.Columns), 29; got != want {
		t.Errorf("got %d columns, want %d", got, want)
	}
	if got, want := table.ColumnNames()[0], "customer_id"; got != want {
		t.Errorf("got %q, want %q", got, want)
	}
	if _, ok := Find("no_such_table"); ok {
		t.Error("no_such_table should not be found")
	}
}

// Checks that every table has a CSV file whose header row matches its
// declared columns, and that no CSV file is left over.
func TestFS(t *testing.T) {
	entries, err := fs.Glob(FS(), "*.csv")
	if err != nil {
		t.Fatal(err)
	}
	if got, want := len(entries), len(Tables); got != want {
		t.Errorf("got %d CSV files, want %d", got, want)
	}
	for _, table := range Tables {
		f, err := table.Open()
		if err != nil {
			t.Errorf("%s: %v", table.Name, err)
			continue
		}
		// Table.Reader validates the header against the columns.
		if _, err := table.Reader(f); err != nil {
			t.Error(err)
		}
		_ = f.Close()
	}
}

func TestReadAll(t *testing.T) {
	for _, test := range []struct {
		name string
		rows int
	}{
		{"days", 7},
		{"product", 1560},
		{"store", 25},
		{"sales_fact_1997", 86837},
	} {
		table, ok := Find(test.name)
		if !ok {
			t.Fatalf("%s not found", test.name)
		}
		rows, err := table.ReadAll()
		if err != nil {
			t.Fatal(err)
		}
		if got, want := len(rows), test.rows; got != want {
			t.Errorf("%s: got %d rows, want %d", test.name, got, want)
		}
	}
}

// Checks that quoted fields containing commas and doubled quotes are
// parsed correctly.
func TestQuoting(t *testing.T) {
	table, _ := Find("account")
	rows, err := table.ReadAll()
	if err != nil {
		t.Fatal(err)
	}
	var found bool
	for _, row := range rows {
		if row[0] == "3100" {
			found = true
			//nolint:lll // a data fixture that cannot be wrapped
			const want = `LookUpCube("[Sales]","(Measures.[Store Sales],"+time.currentmember.UniqueName+","+ Store.currentmember.UniqueName+")")`
			if got := row[5]; got != want {
				t.Errorf("got %q, want %q", got, want)
			}
		}
	}
	if !found {
		t.Error("account 3100 not found")
	}
}

func TestCreateSQL(t *testing.T) {
	table, _ := Find("days")
	want := `CREATE TABLE "days" ("day" INTEGER NOT NULL, ` +
		`"week_day" VARCHAR(30) NOT NULL)`
	if got := table.CreateSQL(); got != want {
		t.Errorf("got %q, want %q", got, want)
	}
	if got, want := table.InsertSQL(),
		`INSERT INTO "days" VALUES (?, ?)`; got != want {
		t.Errorf("got %q, want %q", got, want)
	}
}

func TestValue(t *testing.T) {
	for _, test := range []struct {
		sqlType string
		s       string
		want    any
	}{
		{"INTEGER", "", nil},
		{"INTEGER", "42", int64(42)},
		{"SMALLINT", "-1", int64(-1)},
		{"DECIMAL(10,4)", "1.5000", 1.5},
		{"DOUBLE", "8.39", 8.39},
		{"BOOLEAN", "false", false},
		{"VARCHAR(30)", "Sheri Nowmer", "Sheri Nowmer"},
		{"DATE", "1961-08-26", "1961-08-26"},
	} {
		c := Column{Name: "c", Type: test.sqlType}
		got, err := c.value(test.s)
		if err != nil {
			t.Errorf("%s %q: %v", test.sqlType, test.s, err)
		} else if got != test.want {
			t.Errorf("%s %q: got %v, want %v",
				test.sqlType, test.s, got, test.want)
		}
	}
}

// Reads every row of every table, to check that all CSV files parse and
// that every field converts to its declared type.
func TestReadEverything(t *testing.T) {
	var rows, fields int
	for _, table := range Tables {
		f, err := table.Open()
		if err != nil {
			t.Fatal(err)
		}
		r, err := table.Reader(f)
		if err != nil {
			t.Fatal(err)
		}
		for {
			record, err := r.Read()
			if err == io.EOF {
				break
			}
			if err != nil {
				t.Fatalf("%s: %v", table.Name, err)
			}
			rows++
			for i, c := range table.Columns {
				if _, err := c.value(record[i]); err != nil {
					t.Fatalf("%s.%s: %v", table.Name, c.Name, err)
				}
				fields++
			}
		}
		_ = f.Close()
	}
	if got, want := rows, 328060; got != want {
		t.Errorf("got %d rows, want %d", got, want)
	}
	t.Logf("%d rows, %d fields", rows, fields)
}

// licenseHeader is the Apache header that every Go and Rust source file
// must carry. Comment markers and line breaks are removed before
// comparing, so a file may wrap it however its language prefers.
const licenseHeader = `Licensed to Julian Hyde under one or more contributor license
agreements.  See the NOTICE file distributed with this work for
additional information regarding copyright ownership. Julian Hyde
licenses this file to you under the Apache License, Version 2.0 (the
"License"); you may not use this file except in compliance with the
License.  You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.`

// headerBytes is how much of a file to read looking for the header. The
// header is at the top, so there is no need to normalize a whole file,
// and src/schema.rs is a megabyte of generated data.
const headerBytes = 4096

// normalizeComment strips Go and Rust line-comment markers and collapses
// each run of whitespace to a single space, so that a header can be
// recognized however it is wrapped or commented.
func normalizeComment(s string) string {
	var b strings.Builder
	for _, line := range strings.Split(s, "\n") {
		line = strings.TrimSpace(line)
		line = strings.TrimPrefix(line, "//!") // Rust inner doc comment
		line = strings.TrimPrefix(line, "//")
		b.WriteString(line)
		b.WriteByte(' ')
	}
	return strings.Join(strings.Fields(b.String()), " ")
}

// Checks that every Go and Rust source file starts with the Apache
// license header, including the generated schema.go and src/schema.rs.
func TestLicenseHeader(t *testing.T) {
	want := normalizeComment(licenseHeader)
	counts := map[string]int{}
	err := filepath.WalkDir(".", func(path string, d fs.DirEntry, err error) error {
		if err != nil {
			return err
		}
		if d.IsDir() {
			// Cargo's build output holds copies of the sources, and
			// the Go tool ignores dot-directories.
			if name := d.Name(); path != "." &&
				(name == "target" || strings.HasPrefix(name, ".")) {
				return fs.SkipDir
			}
			return nil
		}
		ext := filepath.Ext(path)
		if ext != ".go" && ext != ".rs" {
			return nil
		}
		f, err := os.Open(path) //nolint:gosec // a path from the tree being tested
		if err != nil {
			return err
		}
		defer f.Close()
		head := make([]byte, headerBytes)
		n, err := io.ReadFull(f, head)
		if err != nil && !errors.Is(err, io.ErrUnexpectedEOF) {
			return err
		}
		if !strings.Contains(normalizeComment(string(head[:n])), want) {
			t.Errorf("%s: missing or altered Apache license header", path)
		}
		counts[ext]++
		return nil
	})
	if err != nil {
		t.Fatal(err)
	}
	// A walk that matched nothing would pass silently.
	for _, ext := range []string{".go", ".rs"} {
		if counts[ext] == 0 {
			t.Errorf("found no %s files to check", ext)
		}
	}
	t.Logf("checked %d Go and %d Rust files",
		counts[".go"], counts[".rs"])
}

// End foodmart_test.go
