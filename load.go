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

package foodmart

import (
	"context"
	"database/sql"
	"errors"
	"fmt"
	"io"
	"strconv"
	"strings"
)

// Load creates every Foodmart table in db and inserts all rows.
//
// This package has no driver of its own; the caller supplies the
// database. For example, using a SQLite driver:
//
//	db, err := sql.Open("sqlite", ":memory:")
//	if err != nil {
//		return err
//	}
//	if err := foodmart.Load(ctx, db); err != nil {
//		return err
//	}
//
// The statements use "?" parameter markers and standard double-quoted
// identifiers; see [Table.InsertSQL]. Everything runs in a single
// transaction, so a failure leaves db unchanged.
func Load(ctx context.Context, db *sql.DB) error {
	tx, err := db.BeginTx(ctx, nil)
	if err != nil {
		return err
	}
	defer func() { _ = tx.Rollback() }()
	for _, t := range Tables {
		if err := t.load(ctx, tx); err != nil {
			return err
		}
	}
	return tx.Commit()
}

// load creates one table and inserts its rows.
func (t Table) load(ctx context.Context, tx *sql.Tx) error {
	if _, err := tx.ExecContext(ctx, t.CreateSQL()); err != nil {
		return fmt.Errorf("%s: %w", t.Name, err)
	}
	stmt, err := tx.PrepareContext(ctx, t.InsertSQL())
	if err != nil {
		return fmt.Errorf("%s: %w", t.Name, err)
	}
	defer stmt.Close()

	f, err := t.Open()
	if err != nil {
		return err
	}
	defer f.Close()
	r, err := t.Reader(f)
	if err != nil {
		return err
	}
	args := make([]any, len(t.Columns))
	for line := 2; ; line++ {
		record, err := r.Read()
		if errors.Is(err, io.EOF) {
			return nil
		}
		if err != nil {
			return fmt.Errorf("%s line %d: %w", t.Name, line, err)
		}
		for i, c := range t.Columns {
			if args[i], err = c.value(record[i]); err != nil {
				return fmt.Errorf("%s line %d, column %q: %w",
					t.Name, line, c.Name, err)
			}
		}
		if _, err := stmt.ExecContext(ctx, args...); err != nil {
			return fmt.Errorf("%s line %d: %w", t.Name, line, err)
		}
	}
}

// value converts a CSV field to a value of the column's SQL type.
// An empty field becomes nil, that is, SQL NULL.
func (c Column) value(s string) (any, error) {
	if s == "" {
		return nil, nil
	}
	switch base(c.Type) {
	case "INTEGER", "SMALLINT", "BIGINT":
		return strconv.ParseInt(s, 10, 64)
	case "DECIMAL", "DOUBLE":
		return strconv.ParseFloat(s, 64)
	case "BOOLEAN":
		return strconv.ParseBool(s)
	default:
		// VARCHAR, DATE and TIMESTAMP are passed through as text.
		return s, nil
	}
}

// base returns a SQL type without its precision, for example "DECIMAL"
// given "DECIMAL(10,4)".
func base(sqlType string) string {
	base, _, _ := strings.Cut(sqlType, "(")
	return base
}

// End load.go
