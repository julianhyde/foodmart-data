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

// Package foodmart provides the Foodmart data set as embedded CSV files.
//
// The data set originated as part of the test suite of the Pentaho
// Mondrian OLAP engine. It contains 26 tables: 7 fact tables, such as
// sales_fact_1997, and 19 dimension tables, such as customer.
//
// [Tables] describes the schema. Each [Table] can be read as CSV, or the
// whole data set can be loaded into a SQL database using [Load].
package foodmart

import (
	"embed"
	"encoding/csv"
	"fmt"
	"io/fs"
	"strings"
)

//go:embed csv/*.csv
var files embed.FS

// Column is a column of a [Table].
type Column struct {
	// Name is the column name, as it appears in the CSV header row.
	Name string
	// Type is the SQL type, for example "VARCHAR(30)" or "DECIMAL(10,4)".
	Type string
	// NotNull is whether the column is declared NOT NULL.
	NotNull bool
}

// Table is a table in the Foodmart data set.
//
// The zero value is not useful; obtain tables from [Tables] or [Find].
type Table struct {
	// Name is the table name, and also the base name of its CSV file.
	Name string
	// Columns are the table's columns, in CSV column order.
	Columns []Column
}

// FS returns the CSV files, one per table, named "<table>.csv".
func FS() fs.FS {
	sub, err := fs.Sub(files, "csv")
	if err != nil {
		// Cannot happen: "csv" is a valid path in the embedded FS.
		panic(err)
	}
	return sub
}

// TableNames returns the names of all tables, in alphabetical order.
func TableNames() []string {
	names := make([]string, len(Tables))
	for i, t := range Tables {
		names[i] = t.Name
	}
	return names
}

// Find returns the table with the given name.
func Find(name string) (Table, bool) {
	for _, t := range Tables {
		if t.Name == name {
			return t, true
		}
	}
	return Table{}, false
}

// ColumnNames returns the table's column names, in CSV column order.
func (t Table) ColumnNames() []string {
	names := make([]string, len(t.Columns))
	for i, c := range t.Columns {
		names[i] = c.Name
	}
	return names
}

// Path returns the table's path within [FS], for example "customer.csv".
func (t Table) Path() string {
	return t.Name + ".csv"
}

// Open returns the table's CSV file, including its header row.
// The caller must close it.
func (t Table) Open() (fs.File, error) {
	return files.Open("csv/" + t.Path())
}

// Reader returns a CSV reader over f that has consumed the header row,
// so that the next read returns the first data row. It also checks that
// the header matches the table's declared columns.
func (t Table) Reader(f fs.File) (*csv.Reader, error) {
	r := csv.NewReader(f)
	r.FieldsPerRecord = len(t.Columns)
	r.ReuseRecord = true
	header, err := r.Read()
	if err != nil {
		return nil, fmt.Errorf("%s: reading header: %w", t.Name, err)
	}
	for i, c := range t.Columns {
		if header[i] != c.Name {
			return nil, fmt.Errorf("%s: column %d is %q, expected %q",
				t.Name, i, header[i], c.Name)
		}
	}
	return r, nil
}

// ReadAll returns every data row of the table. The header row is not
// included. Empty fields represent SQL NULL.
//
// The larger fact tables have over 100,000 rows; to avoid holding them
// all in memory, use [Table.Open] and [Table.Reader] instead.
func (t Table) ReadAll() ([][]string, error) {
	f, err := t.Open()
	if err != nil {
		return nil, err
	}
	defer f.Close()
	r, err := t.Reader(f)
	if err != nil {
		return nil, err
	}
	r.ReuseRecord = false
	return r.ReadAll()
}

// CreateSQL returns a CREATE TABLE statement for the table, with
// identifiers quoted using the SQL standard double-quote.
func (t Table) CreateSQL() string {
	var b strings.Builder
	fmt.Fprintf(&b, "CREATE TABLE %q (", t.Name)
	for i, c := range t.Columns {
		if i > 0 {
			b.WriteString(", ")
		}
		fmt.Fprintf(&b, "%q %s", c.Name, c.Type)
		if c.NotNull {
			b.WriteString(" NOT NULL")
		}
	}
	b.WriteString(")")
	return b.String()
}

// InsertSQL returns an INSERT statement for the table, with one
// positional parameter marker per column.
//
// The marker is "?", which suits SQLite, MySQL and DuckDB. For a
// database that numbers its parameters, such as PostgreSQL, build the
// statement from [Table.ColumnNames] instead.
func (t Table) InsertSQL() string {
	var b strings.Builder
	fmt.Fprintf(&b, "INSERT INTO %q VALUES (", t.Name)
	for i := range t.Columns {
		if i > 0 {
			b.WriteString(", ")
		}
		b.WriteString("?")
	}
	b.WriteString(")")
	return b.String()
}

// End foodmart.go
