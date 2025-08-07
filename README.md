

# Retail Data Pipeline Project (Work in Progress)

## Table of Contents
- [Overview](#overview)
- [Project Structure](#project-structure)
- [Toolkit](#toolkit)
- [Data Quality Checks](#data-quality-checks-with-soda-core)
- [Transformations](#transformations)
- [Reports](#reports)
- [Metabase Dashboard (To Be Added)](#metabase-dashboard-to-be-added)
- [Contributing](#contributing)
- [License](#license)

---

## Overview

**This project is a work in progress** focused on building a **reliable, orchestrated retail data pipeline** using **Apache Airflow, BigQuery, dbt, Soda Core, and Metabase** for visualization.

The goal is to develop **data infrastructure that runs smoothly behind the scenes** — transforming raw retail CSV data into **clean, trustworthy datasets ready for analysis and dashboarding**. My previous pipeline lacked orchestration, so this iteration emphasizes **mastering Airflow to coordinate extraction, transformation, and quality checks**.

---

## Project Structure

```plaintext
.
├── dags/                 # Airflow workflows
├── dbt/                  # dbt project files
│   ├── models/
│   │   ├── report/              # Reporting models
│   │   │   ├── report_customer_invoices.sql
│   │   │   ├── report_product_invoices.sql
│   │   │   └── report_year_invoices.sql
│   │   ├── sources/             # Source definitions
│   │   │   └── sources.yml
│   │   └── transform/           # Dimensional and fact models
│   │       ├── dim_customer.sql
│   │       ├── dim_product.sql
│   │       ├── dim_datetime.sql
│   │       └── fct_invoices.sql
│   ├── macros/                  # dbt macros
│   ├── tests/                   # dbt tests
│   └── dbt_project.yml          # dbt project config
├── include/                    # Configs, credentials, and Soda data quality checks
│   ├── gcp/                     # Google Cloud service account credentials
│   │   └── service_account.json
│   ├── dataset/                 # Sample CSV datasets
│   │   └── online_retail.csv
│   └── soda/checks/             # Soda Core data quality YAML checks
│       ├── report/              # Checks for reporting models
│       │   ├── report_customer_invoices.yml
│       │   ├── report_product_invoices.yml
│       │   └── report_year_invoices.yml
│       ├── sources/             # Checks for sources
│       │   └── raw_invoices.yml
│       └── transform/           # Checks for transformed models
│           ├── dim_customer.yml
│           ├── dim_product.yml
│           ├── dim_datetime.yml
│           └── fct_invoices.yml
├── plugins/                    # Airflow plugins (custom operators/hooks)
├── tests/                      # Tests for DAGs and other components
│   └── dags/
│       └── test_dag_example.py
├── Dockerfile                  # Docker container setup
├── airflow.cfg                 # Airflow configuration
├── requirements.txt            # Python dependencies
├── airflow_settings.yaml       # Airflow environment settings
├── packages.txt                # Additional package requirements
```
---

## Toolkit

| Tool/Technology | Purpose                              |
|-----------------|------------------------------------|
| Apache Airflow  | Orchestration of data workflows    |
| Google BigQuery | Cloud data warehouse                |
| dbt             | SQL-based data transformation      |
| Soda Core       | Automated data quality checks      |
| Metabase        | Dashboard and data visualization   |
| astro-sdk       | Astronomer platform SDK             |
| cosmos          | dbt adapter and extensions          |
| SQL             | Querying and transforming data      |

---

## Data Quality Checks with Soda Core

This project uses **Soda Core** to maintain high data quality. Below are examples of the checks implemented on key dimensional and fact models:

### dim_customer Checks
- **Schema Validation:**  
  Ensures required columns (`customer_id`, `country`) exist and are of the correct data type (`string`).
- **Uniqueness:**  
  Confirms all `customer_id` values are unique.
- **Completeness:**  
  Verifies no missing values in critical columns like `customer_id`.

### dim_datetime Checks
- **Schema Validation:**  
  Confirms required columns (`datetime_id`, `datetime`) are present with correct data types (`string` and `datetime` respectively).
- **Value Range:**  
  Validates that the `weekday` column contains only values between 0 and 6.
- **Uniqueness:**  
  Ensures each `datetime_id` is unique.
- **Completeness:**  
  Checks for no missing `datetime_id` values.

### dim_product Checks
- **Schema Validation:**  
  Requires columns (`product_id`, `description`, `price`) to be present with correct data types (`string` for IDs and descriptions, `float64` for price).
- **Uniqueness:**  
  Ensures all `product_id` values are unique.
- **Completeness:**  
  Checks that every product has a key (`product_id` is not null).
- **Value Constraints:**  
  Validates that product prices are never negative.

### fct_invoices Checks
- **Schema Validation:**  
  Ensures essential columns (`invoice_id`, `product_id`, `customer_id`, `datetime_id`, `quantity`, `total`) exist and are of the expected data types (`string`, `int`, `float64` as appropriate).
- **Completeness:**  
  Confirms no missing `invoice_id` values.
- **Business Rules:**  
  Checks that invoice totals are never negative by running a custom SQL query to identify invalid rows.

---

## Transformations

The pipeline uses **dbt** to transform raw source data into clean, analytics-ready models. Here are some examples:

### dim_customer Model
- Extracts unique customers from raw invoice data by combining `CustomerID` and `Country` into a surrogate key.  
- Adds country information by joining with a reference table containing country ISO codes.  
- Filters out records missing `CustomerID` to ensure data accuracy.

### dim_datetime Model
- Parses raw invoice date strings of varying formats into a consistent datetime format.  
- Extracts key date and time parts like year, month, day, hour, minute, and weekday to support time-based analysis.  
- Produces a clean date dimension table with unique datetime keys.

### dim_product Model
- Handles product records where the same stock code may have different descriptions or prices by creating a surrogate key based on stock code, description, and price.  
- Selects distinct product combinations with positive prices only, filtering out invalid data.  
- Creates a clean product dimension table for use in sales and inventory analysis.

### fct_invoices Model
- Builds the fact table by combining sales invoice data with keys from the dimension tables.  
- Generates surrogate keys for products and customers to link related data.  
- Filters out invoice rows where quantity is zero or negative.  
- Calculates total sale amount as quantity multiplied by unit price.  
- Joins with dimension tables (`dim_datetime`, `dim_product`, `dim_customer`) to ensure consistent, clean foreign keys.

Together, these models form a star schema that makes querying retail data intuitive and efficient for analysts and data users.

---

## Reports

In addition to core dimensional and fact models, this project includes report models to generate actionable insights.

### report_customer_invoices
- Aggregates sales invoices by customer country.  
- Calculates total number of invoices and total revenue per country.  
- Orders countries by revenue to highlight the top markets.  
- Useful for understanding geographic sales performance at a glance.

### report_product_invoices
- Summarizes total quantity sold per product.  
- Groups by product ID, stock code, and description to provide detailed product sales insights.  
- Orders products by quantity sold to identify best sellers.  
- Helps inform inventory and marketing decisions.

### report_year_invoices
- Aggregates invoice counts and revenue by year and month.  
- Enables trend analysis over time to track seasonal patterns and growth.  
- Useful for financial reporting and forecasting.

---

## Metabase Dashboard (To Be Added)

A dashboard will visualize the retail data pipeline outputs, offering:

- Interactive insights into sales trends by geography, product, and time.
- Support for decision-makers with real-time, trustworthy metrics.
- Easy exploration of data quality and pipeline health.



---
Stay tuned for details as this section is developed.

---

*Thank you for exploring this retail data pipeline project!*
