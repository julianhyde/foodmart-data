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

//! Kick the tires.

use foodmart_data::{find, table_names, TABLES};

#[test]
fn test_table_names() {
    let names: Vec<_> = table_names().collect();
    assert_eq!(names.len(), 26);
    assert_eq!(names[0], "account");
    assert_eq!(names[25], "warehouse_class");
    assert!(
        !names.iter().any(|n| n.starts_with("agg_")),
        "aggregate tables should not be present"
    );
    let mut sorted = names.clone();
    sorted.sort_unstable();
    assert_eq!(names, sorted, "tables should be in alphabetical order");
}

#[test]
fn test_find() {
    let table = find("customer").unwrap();
    assert_eq!(table.columns.len(), 29);
    assert_eq!(table.column_names()[0], "customer_id");
    assert!(find("no_such_table").is_none());
}

/// Checks that each table's header row matches its declared columns.
#[test]
fn test_header() {
    for table in &TABLES {
        assert_eq!(
            table.header(),
            table.column_names(),
            "{} header does not match its columns",
            table.name
        );
    }
}

#[test]
fn test_row_counts() {
    for (name, want) in [
        ("days", 7),
        ("product", 1560),
        ("store", 25),
        ("sales_fact_1997", 86837),
    ] {
        assert_eq!(find(name).unwrap().rows().count(), want, "{name}");
    }
}

/// Checks that quoted fields containing commas and doubled quotes are
/// parsed correctly.
#[test]
fn test_quoting() {
    let table = find("account").unwrap();
    let row = table.rows().find(|r| r[0] == "3100").unwrap();
    assert_eq!(
        row[5],
        r#"LookUpCube("[Sales]","(Measures.[Store Sales],"+time.currentmember.UniqueName+","+ Store.currentmember.UniqueName+")")"#
    );

    // A quoted field containing a comma.
    let table = find("warehouse").unwrap();
    let row = table.rows().find(|r| r[0] == "3").unwrap();
    assert_eq!(row[3], "Destination, Inc.");

    // Trailing empty fields, and an interior run of them.
    let row = find("store").unwrap().rows().find(|r| r[0] == "0").unwrap();
    assert_eq!(row.len(), find("store").unwrap().columns.len());
}

#[test]
fn test_create_table_sql() {
    let table = find("days").unwrap();
    assert_eq!(
        table.create_table_sql(),
        r#"CREATE TABLE "days" ("day" INTEGER NOT NULL, "week_day" VARCHAR(30) NOT NULL)"#
    );
}

#[test]
fn test_insert_sql() {
    let table = find("days").unwrap();
    let row = table.rows().next().unwrap();
    assert_eq!(
        table.insert_sql(&row),
        r#"INSERT INTO "days" VALUES (1, 'Sunday')"#
    );

    // Nulls, and apostrophes doubled.
    let table = find("account").unwrap();
    let row = table.rows().find(|r| r[0] == "1000").unwrap();
    assert!(table.insert_sql(&row).ends_with("NULL)"));
}

/// Reads every row of every table, checking that each row has one field
/// per column and that numeric fields parse.
#[test]
fn test_read_everything() {
    let mut rows = 0;
    for table in &TABLES {
        for row in table.rows() {
            assert_eq!(
                row.len(),
                table.columns.len(),
                "{} row {}: got {} fields",
                table.name,
                rows,
                row.len()
            );
            for (c, v) in table.columns.iter().zip(&row) {
                assert!(
                    !(v.is_empty() && c.not_null),
                    "{}.{}: null in a NOT NULL column",
                    table.name,
                    c.name
                );
                if v.is_empty() {
                    continue;
                }
                match c.base_type() {
                    "INTEGER" | "SMALLINT" | "BIGINT" => {
                        v.parse::<i64>().unwrap_or_else(|e| {
                            panic!("{}.{} = {v:?}: {e}", table.name, c.name)
                        });
                    }
                    "DECIMAL" | "DOUBLE" => {
                        v.parse::<f64>().unwrap_or_else(|e| {
                            panic!("{}.{} = {v:?}: {e}", table.name, c.name)
                        });
                    }
                    "BOOLEAN" => {
                        v.parse::<bool>().unwrap_or_else(|e| {
                            panic!("{}.{} = {v:?}: {e}", table.name, c.name)
                        });
                    }
                    _ => {}
                }
            }
            rows += 1;
        }
    }
    assert_eq!(rows, 328_060);
}

// End basic.rs
