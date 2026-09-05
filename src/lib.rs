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

//! The Foodmart data set, as embedded CSV files.
//!
//! The data set originated as part of the test suite of the Pentaho
//! Mondrian OLAP engine. It contains 26 tables: 7 fact tables, such as
//! `sales_fact_1997`, and 19 dimension tables, such as `customer`.
//!
//! [`TABLES`] describes the schema; each [`Table`] carries its own CSV
//! text, so there are no files to find at run time.
//!
//! ```
//! let table = foodmart_data::find("days").unwrap();
//! assert_eq!(table.column_names(), ["day", "week_day"]);
//! assert_eq!(table.rows().count(), 7);
//! ```
//!
//! The crate has no dependencies and does not link a database. To load
//! the data, generate DDL and DML with [`Table::create_table_sql`] and
//! [`Table::insert_sql`] and execute them against a database of your
//! choice.

#![forbid(unsafe_code)]
#![warn(missing_docs)]

use std::borrow::Cow;
use std::fmt::Write as _;

mod schema;

pub use schema::TABLES;

/// Value of the `not_null` argument to [`Column::new`], for a column
/// that may contain nulls.
pub(crate) const NULL: bool = false;

/// Value of the `not_null` argument to [`Column::new`], for a column
/// that is declared `NOT NULL`.
pub(crate) const NOT_NULL: bool = true;

/// A column of a [`Table`].
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct Column {
    /// The column name, as it appears in the CSV header row.
    pub name: &'static str,
    /// The SQL type, for example `"VARCHAR(30)"` or `"DECIMAL(10,4)"`.
    pub sql_type: &'static str,
    /// Whether the column is declared `NOT NULL`.
    pub not_null: bool,
}

/// A table in the Foodmart data set.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct Table {
    /// The table name, and also the base name of its CSV file.
    pub name: &'static str,
    /// The table's columns, in CSV column order.
    pub columns: &'static [Column],
    /// The contents of the table's CSV file, including the header row.
    pub csv: &'static str,
}

/// Returns the names of all tables, in alphabetical order.
pub fn table_names() -> impl Iterator<Item = &'static str> {
    TABLES.iter().map(|t| t.name)
}

/// Returns the table with the given name.
pub fn find(name: &str) -> Option<&'static Table> {
    TABLES.iter().find(|t| t.name == name)
}

impl Table {
    /// Returns the table's column names, in CSV column order.
    pub fn column_names(&self) -> Vec<&'static str> {
        self.columns.iter().map(|c| c.name).collect()
    }

    /// Returns the header row of the CSV file, as field names.
    ///
    /// This is always equal to [`Table::column_names`]; the crate's
    /// tests check that it is.
    pub fn header(&self) -> Vec<Cow<'static, str>> {
        parse_record(self.csv.lines().next().unwrap_or(""))
    }

    /// Returns the table's data rows. The header row is skipped.
    ///
    /// An empty field represents SQL `NULL`, and is yielded as an empty
    /// string; consult [`Column::not_null`] to tell an empty string
    /// from a null.
    pub fn rows(&self) -> Rows {
        let mut lines = self.csv.lines();
        lines.next(); // discard the header row
        Rows { lines }
    }

    /// Returns a `CREATE TABLE` statement for the table, with
    /// identifiers quoted using the SQL standard double-quote.
    ///
    /// ```
    /// let table = foodmart_data::find("days").unwrap();
    /// assert_eq!(
    ///     table.create_table_sql(),
    ///     r#"CREATE TABLE "days" ("day" INTEGER NOT NULL, "week_day" VARCHAR(30) NOT NULL)"#);
    /// ```
    pub fn create_table_sql(&self) -> String {
        let mut s = format!("CREATE TABLE \"{}\" (", self.name);
        for (i, c) in self.columns.iter().enumerate() {
            if i > 0 {
                s.push_str(", ");
            }
            let _ = write!(s, "\"{}\" {}", c.name, c.sql_type);
            if c.not_null {
                s.push_str(" NOT NULL");
            }
        }
        s.push(')');
        s
    }

    /// Returns an `INSERT` statement for one row, as literal SQL.
    ///
    /// Values of character, date and timestamp columns are quoted;
    /// numeric and boolean values are not; an empty field becomes
    /// `NULL`.
    ///
    /// # Panics
    ///
    /// Panics if `row` does not have one value per column.
    pub fn insert_sql(&self, row: &[Cow<'_, str>]) -> String {
        assert_eq!(
            row.len(),
            self.columns.len(),
            "{}: got {} values, want {}",
            self.name,
            row.len(),
            self.columns.len()
        );
        let mut s = format!("INSERT INTO \"{}\" VALUES (", self.name);
        for (i, (c, v)) in self.columns.iter().zip(row).enumerate() {
            if i > 0 {
                s.push_str(", ");
            }
            if v.is_empty() {
                s.push_str("NULL");
            } else if c.is_character() {
                let _ = write!(s, "'{}'", v.replace('\'', "''"));
            } else {
                s.push_str(v);
            }
        }
        s.push(')');
        s
    }
}

impl Column {
    /// Creates a column, given its name, its SQL type, and whether it
    /// is declared `NOT NULL`.
    #[must_use]
    pub const fn new(
        name: &'static str,
        sql_type: &'static str,
        not_null: bool,
    ) -> Self {
        Self {
            name,
            sql_type,
            not_null,
        }
    }

    /// Returns the SQL type without its precision, for example
    /// `"DECIMAL"` given `"DECIMAL(10,4)"`.
    pub fn base_type(&self) -> &'static str {
        match self.sql_type.find('(') {
            Some(i) => &self.sql_type[..i],
            None => self.sql_type,
        }
    }

    /// Returns whether values of this column need quoting in SQL.
    pub fn is_character(&self) -> bool {
        matches!(self.base_type(), "VARCHAR" | "CHAR" | "DATE" | "TIMESTAMP")
    }
}

/// An iterator over the data rows of a [`Table`], created by
/// [`Table::rows`].
#[derive(Clone, Debug)]
pub struct Rows {
    lines: std::str::Lines<'static>,
}

impl Iterator for Rows {
    type Item = Vec<Cow<'static, str>>;

    fn next(&mut self) -> Option<Self::Item> {
        loop {
            let line = self.lines.next()?;
            if !line.is_empty() {
                return Some(parse_record(line));
            }
        }
    }
}

/// Splits one line of CSV into fields.
///
/// Follows RFC 4180: a field may be enclosed in double quotes, within
/// which a doubled double-quote denotes a single one. A field that
/// needs no unescaping borrows from the input rather than allocating.
fn parse_record(line: &str) -> Vec<Cow<'_, str>> {
    let mut fields = Vec::new();
    let bytes = line.as_bytes();
    let mut i = 0;
    loop {
        if i < bytes.len() && bytes[i] == b'"' {
            // A quoted field. Scan for the closing quote, treating a
            // doubled quote as an escaped one.
            let mut value = String::new();
            let mut start = i + 1;
            let mut j = start;
            while j < bytes.len() {
                if bytes[j] == b'"' {
                    if bytes.get(j + 1) == Some(&b'"') {
                        value.push_str(&line[start..j + 1]);
                        j += 2;
                        start = j;
                        continue;
                    }
                    break;
                }
                j += 1;
            }
            value.push_str(&line[start..j.min(bytes.len())]);
            fields.push(Cow::Owned(value));
            // Skip the closing quote and the following comma, if any.
            i = (j + 1).min(bytes.len());
        } else {
            let j = bytes[i..]
                .iter()
                .position(|&b| b == b',')
                .map_or(bytes.len(), |k| i + k);
            fields.push(Cow::Borrowed(&line[i..j]));
            i = j;
        }
        if i >= bytes.len() {
            return fields;
        }
        debug_assert_eq!(bytes[i], b',');
        i += 1;
        if i == bytes.len() {
            // A trailing comma means a final empty field.
            fields.push(Cow::Borrowed(""));
            return fields;
        }
    }
}

// End lib.rs
