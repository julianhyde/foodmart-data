#!/usr/bin/env python3
# Licensed to Julian Hyde under one or more contributor license
# agreements.  See the NOTICE file distributed with this work
# for additional information regarding copyright ownership.
# Julian Hyde licenses this file to you under the Apache
# License, Version 2.0 (the "License"); you may not use this
# file except in compliance with the License.  You may obtain a
# copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
# either express or implied.  See the License for the specific
# language governing permissions and limitations under the
# License.

"""The Foodmart schema, and a generator for schema.go and src/schema.rs.

SCHEMA is the definitive description of the data set: one entry per
table, and within it one entry per column, in CSV column order. It
matches the header row of the corresponding file in csv/.

The types are those of the foodmart-data-hsqldb project, from which the
CSV files are taken. The 11 aggregate tables of that project, whose
names start with "agg_", are deliberately absent; see README.md.

Running this script regenerates schema.go and src/schema.rs, and checks every column
against the header row of its CSV file, so the schema and the data
cannot drift apart unnoticed:

    ./tools/schema.py
"""

import os
import shutil
import subprocess
import sys

# Whether a column is declared NOT NULL, for use in SCHEMA.
NULL = False
NOT_NULL = True

# The Foodmart schema: (table, ((column, SQL type, nullability), ...)).
SCHEMA = (
    ("account", (
        ("account_id", "INTEGER", NOT_NULL),
        ("account_parent", "INTEGER", NULL),
        ("account_description", "VARCHAR(30)", NULL),
        ("account_type", "VARCHAR(30)", NOT_NULL),
        ("account_rollup", "VARCHAR(30)", NOT_NULL),
        ("Custom_Members", "VARCHAR(255)", NULL),
    )),
    ("category", (
        ("category_id", "VARCHAR(30)", NOT_NULL),
        ("category_parent", "VARCHAR(30)", NULL),
        ("category_description", "VARCHAR(30)", NOT_NULL),
        ("category_rollup", "VARCHAR(30)", NULL),
    )),
    ("currency", (
        ("currency_id", "INTEGER", NOT_NULL),
        ("date", "DATE", NOT_NULL),
        ("currency", "VARCHAR(30)", NOT_NULL),
        ("conversion_ratio", "DECIMAL(10,4)", NOT_NULL),
    )),
    ("customer", (
        ("customer_id", "INTEGER", NOT_NULL),
        ("account_num", "BIGINT", NOT_NULL),
        ("lname", "VARCHAR(30)", NOT_NULL),
        ("fname", "VARCHAR(30)", NOT_NULL),
        ("mi", "VARCHAR(30)", NULL),
        ("address1", "VARCHAR(30)", NULL),
        ("address2", "VARCHAR(30)", NULL),
        ("address3", "VARCHAR(30)", NULL),
        ("address4", "VARCHAR(30)", NULL),
        ("city", "VARCHAR(30)", NULL),
        ("state_province", "VARCHAR(30)", NULL),
        ("postal_code", "VARCHAR(30)", NOT_NULL),
        ("country", "VARCHAR(30)", NOT_NULL),
        ("customer_region_id", "INTEGER", NOT_NULL),
        ("phone1", "VARCHAR(30)", NOT_NULL),
        ("phone2", "VARCHAR(30)", NOT_NULL),
        ("birthdate", "DATE", NOT_NULL),
        ("marital_status", "VARCHAR(30)", NOT_NULL),
        ("yearly_income", "VARCHAR(30)", NOT_NULL),
        ("gender", "VARCHAR(30)", NOT_NULL),
        ("total_children", "SMALLINT", NOT_NULL),
        ("num_children_at_home", "SMALLINT", NOT_NULL),
        ("education", "VARCHAR(30)", NOT_NULL),
        ("date_accnt_opened", "DATE", NOT_NULL),
        ("member_card", "VARCHAR(30)", NULL),
        ("occupation", "VARCHAR(30)", NULL),
        ("houseowner", "VARCHAR(30)", NULL),
        ("num_cars_owned", "INTEGER", NULL),
        ("fullname", "VARCHAR(60)", NOT_NULL),
    )),
    ("days", (
        ("day", "INTEGER", NOT_NULL),
        ("week_day", "VARCHAR(30)", NOT_NULL),
    )),
    ("department", (
        ("department_id", "INTEGER", NOT_NULL),
        ("department_description", "VARCHAR(30)", NOT_NULL),
    )),
    ("employee", (
        ("employee_id", "INTEGER", NOT_NULL),
        ("full_name", "VARCHAR(30)", NOT_NULL),
        ("first_name", "VARCHAR(30)", NOT_NULL),
        ("last_name", "VARCHAR(30)", NOT_NULL),
        ("position_id", "INTEGER", NULL),
        ("position_title", "VARCHAR(30)", NULL),
        ("store_id", "INTEGER", NOT_NULL),
        ("department_id", "INTEGER", NOT_NULL),
        ("birth_date", "DATE", NOT_NULL),
        ("hire_date", "TIMESTAMP", NULL),
        ("end_date", "TIMESTAMP", NULL),
        ("salary", "DECIMAL(10,4)", NOT_NULL),
        ("supervisor_id", "INTEGER", NULL),
        ("education_level", "VARCHAR(30)", NOT_NULL),
        ("marital_status", "VARCHAR(30)", NOT_NULL),
        ("gender", "VARCHAR(30)", NOT_NULL),
        ("management_role", "VARCHAR(30)", NULL),
    )),
    ("employee_closure", (
        ("employee_id", "INTEGER", NOT_NULL),
        ("supervisor_id", "INTEGER", NOT_NULL),
        ("distance", "INTEGER", NULL),
    )),
    ("expense_fact", (
        ("store_id", "INTEGER", NOT_NULL),
        ("account_id", "INTEGER", NOT_NULL),
        ("exp_date", "TIMESTAMP", NOT_NULL),
        ("time_id", "INTEGER", NOT_NULL),
        ("category_id", "VARCHAR(30)", NOT_NULL),
        ("currency_id", "INTEGER", NOT_NULL),
        ("amount", "DECIMAL(10,4)", NOT_NULL),
    )),
    ("inventory_fact_1997", (
        ("product_id", "INTEGER", NOT_NULL),
        ("time_id", "INTEGER", NULL),
        ("warehouse_id", "INTEGER", NULL),
        ("store_id", "INTEGER", NULL),
        ("units_ordered", "INTEGER", NULL),
        ("units_shipped", "INTEGER", NULL),
        ("warehouse_sales", "DECIMAL(10,4)", NULL),
        ("warehouse_cost", "DECIMAL(10,4)", NULL),
        ("supply_time", "SMALLINT", NULL),
        ("store_invoice", "DECIMAL(10,4)", NULL),
    )),
    ("inventory_fact_1998", (
        ("product_id", "INTEGER", NOT_NULL),
        ("time_id", "INTEGER", NULL),
        ("warehouse_id", "INTEGER", NULL),
        ("store_id", "INTEGER", NULL),
        ("units_ordered", "INTEGER", NULL),
        ("units_shipped", "INTEGER", NULL),
        ("warehouse_sales", "DECIMAL(10,4)", NULL),
        ("warehouse_cost", "DECIMAL(10,4)", NULL),
        ("supply_time", "SMALLINT", NULL),
        ("store_invoice", "DECIMAL(10,4)", NULL),
    )),
    ("position", (
        ("position_id", "INTEGER", NOT_NULL),
        ("position_title", "VARCHAR(30)", NOT_NULL),
        ("pay_type", "VARCHAR(30)", NOT_NULL),
        ("min_scale", "DECIMAL(10,4)", NOT_NULL),
        ("max_scale", "DECIMAL(10,4)", NOT_NULL),
        ("management_role", "VARCHAR(30)", NOT_NULL),
    )),
    ("product", (
        ("product_class_id", "INTEGER", NOT_NULL),
        ("product_id", "INTEGER", NOT_NULL),
        ("brand_name", "VARCHAR(60)", NULL),
        ("product_name", "VARCHAR(60)", NOT_NULL),
        ("SKU", "BIGINT", NOT_NULL),
        ("SRP", "DECIMAL(10,4)", NULL),
        ("gross_weight", "DOUBLE", NULL),
        ("net_weight", "DOUBLE", NULL),
        ("recyclable_package", "BOOLEAN", NULL),
        ("low_fat", "BOOLEAN", NULL),
        ("units_per_case", "SMALLINT", NULL),
        ("cases_per_pallet", "SMALLINT", NULL),
        ("shelf_width", "DOUBLE", NULL),
        ("shelf_height", "DOUBLE", NULL),
        ("shelf_depth", "DOUBLE", NULL),
    )),
    ("product_class", (
        ("product_class_id", "INTEGER", NOT_NULL),
        ("product_subcategory", "VARCHAR(30)", NULL),
        ("product_category", "VARCHAR(30)", NULL),
        ("product_department", "VARCHAR(30)", NULL),
        ("product_family", "VARCHAR(30)", NULL),
    )),
    ("promotion", (
        ("promotion_id", "INTEGER", NOT_NULL),
        ("promotion_district_id", "INTEGER", NULL),
        ("promotion_name", "VARCHAR(30)", NULL),
        ("media_type", "VARCHAR(30)", NULL),
        ("cost", "DECIMAL(10,4)", NULL),
        ("start_date", "TIMESTAMP", NULL),
        ("end_date", "TIMESTAMP", NULL),
    )),
    ("region", (
        ("region_id", "INTEGER", NOT_NULL),
        ("sales_city", "VARCHAR(30)", NULL),
        ("sales_state_province", "VARCHAR(30)", NULL),
        ("sales_district", "VARCHAR(30)", NULL),
        ("sales_region", "VARCHAR(30)", NULL),
        ("sales_country", "VARCHAR(30)", NULL),
        ("sales_district_id", "INTEGER", NULL),
    )),
    ("reserve_employee", (
        ("employee_id", "INTEGER", NOT_NULL),
        ("full_name", "VARCHAR(30)", NOT_NULL),
        ("first_name", "VARCHAR(30)", NOT_NULL),
        ("last_name", "VARCHAR(30)", NOT_NULL),
        ("position_id", "INTEGER", NULL),
        ("position_title", "VARCHAR(30)", NULL),
        ("store_id", "INTEGER", NOT_NULL),
        ("department_id", "INTEGER", NOT_NULL),
        ("birth_date", "TIMESTAMP", NOT_NULL),
        ("hire_date", "TIMESTAMP", NULL),
        ("end_date", "TIMESTAMP", NULL),
        ("salary", "DECIMAL(10,4)", NOT_NULL),
        ("supervisor_id", "INTEGER", NULL),
        ("education_level", "VARCHAR(30)", NOT_NULL),
        ("marital_status", "VARCHAR(30)", NOT_NULL),
        ("gender", "VARCHAR(30)", NOT_NULL),
    )),
    ("salary", (
        ("pay_date", "TIMESTAMP", NOT_NULL),
        ("employee_id", "INTEGER", NOT_NULL),
        ("department_id", "INTEGER", NOT_NULL),
        ("currency_id", "INTEGER", NOT_NULL),
        ("salary_paid", "DECIMAL(10,4)", NOT_NULL),
        ("overtime_paid", "DECIMAL(10,4)", NOT_NULL),
        ("vacation_accrued", "DOUBLE", NOT_NULL),
        ("vacation_used", "DOUBLE", NOT_NULL),
    )),
    ("sales_fact_1997", (
        ("product_id", "INTEGER", NOT_NULL),
        ("time_id", "INTEGER", NOT_NULL),
        ("customer_id", "INTEGER", NOT_NULL),
        ("promotion_id", "INTEGER", NOT_NULL),
        ("store_id", "INTEGER", NOT_NULL),
        ("store_sales", "DECIMAL(10,4)", NOT_NULL),
        ("store_cost", "DECIMAL(10,4)", NOT_NULL),
        ("unit_sales", "DECIMAL(10,4)", NOT_NULL),
    )),
    ("sales_fact_1998", (
        ("product_id", "INTEGER", NOT_NULL),
        ("time_id", "INTEGER", NOT_NULL),
        ("customer_id", "INTEGER", NOT_NULL),
        ("promotion_id", "INTEGER", NOT_NULL),
        ("store_id", "INTEGER", NOT_NULL),
        ("store_sales", "DECIMAL(10,4)", NOT_NULL),
        ("store_cost", "DECIMAL(10,4)", NOT_NULL),
        ("unit_sales", "DECIMAL(10,4)", NOT_NULL),
    )),
    ("sales_fact_dec_1998", (
        ("product_id", "INTEGER", NOT_NULL),
        ("time_id", "INTEGER", NOT_NULL),
        ("customer_id", "INTEGER", NOT_NULL),
        ("promotion_id", "INTEGER", NOT_NULL),
        ("store_id", "INTEGER", NOT_NULL),
        ("store_sales", "DECIMAL(10,4)", NOT_NULL),
        ("store_cost", "DECIMAL(10,4)", NOT_NULL),
        ("unit_sales", "DECIMAL(10,4)", NOT_NULL),
    )),
    ("store", (
        ("store_id", "INTEGER", NOT_NULL),
        ("store_type", "VARCHAR(30)", NULL),
        ("region_id", "INTEGER", NULL),
        ("store_name", "VARCHAR(30)", NULL),
        ("store_number", "INTEGER", NULL),
        ("store_street_address", "VARCHAR(30)", NULL),
        ("store_city", "VARCHAR(30)", NULL),
        ("store_state", "VARCHAR(30)", NULL),
        ("store_postal_code", "VARCHAR(30)", NULL),
        ("store_country", "VARCHAR(30)", NULL),
        ("store_manager", "VARCHAR(30)", NULL),
        ("store_phone", "VARCHAR(30)", NULL),
        ("store_fax", "VARCHAR(30)", NULL),
        ("first_opened_date", "TIMESTAMP", NULL),
        ("last_remodel_date", "TIMESTAMP", NULL),
        ("store_sqft", "INTEGER", NULL),
        ("grocery_sqft", "INTEGER", NULL),
        ("frozen_sqft", "INTEGER", NULL),
        ("meat_sqft", "INTEGER", NULL),
        ("coffee_bar", "BOOLEAN", NULL),
        ("video_store", "BOOLEAN", NULL),
        ("salad_bar", "BOOLEAN", NULL),
        ("prepared_food", "BOOLEAN", NULL),
        ("florist", "BOOLEAN", NULL),
    )),
    ("store_ragged", (
        ("store_id", "INTEGER", NOT_NULL),
        ("store_type", "VARCHAR(30)", NULL),
        ("region_id", "INTEGER", NULL),
        ("store_name", "VARCHAR(30)", NULL),
        ("store_number", "INTEGER", NULL),
        ("store_street_address", "VARCHAR(30)", NULL),
        ("store_city", "VARCHAR(30)", NULL),
        ("store_state", "VARCHAR(30)", NULL),
        ("store_postal_code", "VARCHAR(30)", NULL),
        ("store_country", "VARCHAR(30)", NULL),
        ("store_manager", "VARCHAR(30)", NULL),
        ("store_phone", "VARCHAR(30)", NULL),
        ("store_fax", "VARCHAR(30)", NULL),
        ("first_opened_date", "TIMESTAMP", NULL),
        ("last_remodel_date", "TIMESTAMP", NULL),
        ("store_sqft", "INTEGER", NULL),
        ("grocery_sqft", "INTEGER", NULL),
        ("frozen_sqft", "INTEGER", NULL),
        ("meat_sqft", "INTEGER", NULL),
        ("coffee_bar", "BOOLEAN", NULL),
        ("video_store", "BOOLEAN", NULL),
        ("salad_bar", "BOOLEAN", NULL),
        ("prepared_food", "BOOLEAN", NULL),
        ("florist", "BOOLEAN", NULL),
    )),
    ("time_by_day", (
        ("time_id", "INTEGER", NOT_NULL),
        ("the_date", "TIMESTAMP", NULL),
        ("the_day", "VARCHAR(30)", NULL),
        ("the_month", "VARCHAR(30)", NULL),
        ("the_year", "SMALLINT", NULL),
        ("day_of_month", "SMALLINT", NULL),
        ("week_of_year", "INTEGER", NULL),
        ("month_of_year", "SMALLINT", NULL),
        ("quarter", "VARCHAR(30)", NULL),
        ("fiscal_period", "VARCHAR(30)", NULL),
    )),
    ("warehouse", (
        ("warehouse_id", "INTEGER", NOT_NULL),
        ("warehouse_class_id", "INTEGER", NULL),
        ("stores_id", "INTEGER", NULL),
        ("warehouse_name", "VARCHAR(60)", NULL),
        ("wa_address1", "VARCHAR(30)", NULL),
        ("wa_address2", "VARCHAR(30)", NULL),
        ("wa_address3", "VARCHAR(30)", NULL),
        ("wa_address4", "VARCHAR(30)", NULL),
        ("warehouse_city", "VARCHAR(30)", NULL),
        ("warehouse_state_province", "VARCHAR(30)", NULL),
        ("warehouse_postal_code", "VARCHAR(30)", NULL),
        ("warehouse_country", "VARCHAR(30)", NULL),
        ("warehouse_owner_name", "VARCHAR(30)", NULL),
        ("warehouse_phone", "VARCHAR(30)", NULL),
        ("warehouse_fax", "VARCHAR(30)", NULL),
    )),
    ("warehouse_class", (
        ("warehouse_class_id", "INTEGER", NOT_NULL),
        ("description", "VARCHAR(30)", NULL),
    )),
)

LICENSE = """// Licensed to Julian Hyde under one or more contributor license
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

// Code generated by tools/schema.py. DO NOT EDIT."""


def check(csv_dir):
    """Checks each table's columns against the header row of its CSV file."""
    for name, columns in SCHEMA:
        path = os.path.join(csv_dir, name + '.csv')
        if not os.path.exists(path):
            sys.exit('%s: no such file' % path)
        with open(path) as f:
            header = f.readline().rstrip('\n').split(',')
        expected = [c[0] for c in columns]
        if header != expected:
            sys.exit('%s.csv: header is %s, expected %s'
                     % (name, header, expected))
    extra = (set(f[:-4] for f in os.listdir(csv_dir) if f.endswith('.csv'))
             - set(name for name, _ in SCHEMA))
    if extra:
        sys.exit('CSV files with no table in SCHEMA: %s'
                 % ', '.join(sorted(extra)))


def write_go(path):
    b = [LICENSE, '', 'package foodmart', '',
         '// Tables describes every table in the data set, in alphabetical',
         '// order.',
         'var Tables = []Table{']
    for name, columns in SCHEMA:
        b.append('\t{')
        b.append('\t\tName: "%s",' % name)
        b.append('\t\tColumns: []Column{')
        for cn, ct, nn in columns:
            b.append('\t\t\t{Name: "%s", Type: "%s", NotNull: %s},'
                     % (cn, ct, 'true' if nn else 'false'))
        b.append('\t\t},')
        b.append('\t},')
    b += ['}', '', '// End schema.go']
    open(path, 'w').write('\n'.join(b) + '\n')


def write_rust(path):
    b = [LICENSE.replace('// Code generated', '//! Code generated'), '',
         'use crate::{Column, Table, NOT_NULL, NULL};', '',
         '/// Every table in the data set, in alphabetical order.',
         'pub static TABLES: [Table; %d] = [' % len(SCHEMA)]
    for name, columns in SCHEMA:
        b.append('    Table {')
        b.append('        name: "%s",' % name)
        b.append('        csv: include_str!("../csv/%s.csv"),' % name)
        b.append('        columns: &[')
        for cn, ct, nn in columns:
            b.append('            Column::new("%s", "%s", %s),'
                     % (cn, ct, 'NOT_NULL' if nn else 'NULL'))
        b.append('        ],')
        b.append('    },')
    b += ['];', '', '// End schema.rs']
    open(path, 'w').write('\n'.join(b) + '\n')


def reformat(tool, args, path):
    """Runs a formatter over a generated file, if it is installed.

    Keeping the generated files formatted means that regenerating them
    never produces a diff that "gofmt -l" or "cargo fmt --check" would
    then complain about.
    """
    if shutil.which(tool):
        subprocess.run([tool] + args + [path], check=True)


def main():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    check(os.path.join(root, 'csv'))

    go_path = os.path.join(root, 'schema.go')
    write_go(go_path)
    reformat('gofmt', ['-w'], go_path)

    rust_path = os.path.join(root, 'src', 'schema.rs')
    write_rust(rust_path)
    reformat('rustfmt', ['--edition', '2021'], rust_path)

    print('%d tables, %d columns'
          % (len(SCHEMA), sum(len(c) for _, c in SCHEMA)))


if __name__ == '__main__':
    main()

# End schema.py
