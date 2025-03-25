# Fabric notebook source

# METADATA ********************

# META {
# META   "kernel_info": {
# META     "name": "synapse_pyspark"
# META   },
# META   "dependencies": {
# META     "lakehouse": {
# META       "default_lakehouse": "af437dae-ba73-4f9a-87a9-b7b773d87122",
# META       "default_lakehouse_name": "Ecom_LH",
# META       "default_lakehouse_workspace_id": "7df11103-dbbf-44c8-b7ad-434288bbc9e0"
# META     }
# META   }
# META }

# CELL ********************

# Welcome to your new notebook
# Type here in the cell editor to add code!


# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

import re
from pyspark.sql.functions import col
from pyspark.sql import SparkSession

def save_each_csv_as_delta(folder_path="Files"):
    # Step 1: Get list of all CSV files using Spark's file listing
    file_list_df = spark.read.format("binaryFile").load(folder_path + "/*.csv")
    file_paths = [row.path for row in file_list_df.select("path").collect()]

    # Step 2: Loop through each file and save separately
    for full_path in file_paths:
        # Extract file name without extension (e.g., "2020-Jan")
        match = re.search(r'([^/]+)\.csv$', full_path)
        file_name = match.group(1).replace("-", "_") if match else "unknown_file"

        # Read CSV
        df = spark.read.option("header", True).csv(full_path)

        # Clean types (optional)
        df = df.withColumn("price", col("price").cast("double")) \
               .withColumn("user_id", col("user_id").cast("string")) \
               .withColumn("product_id", col("product_id").cast("string"))

        # Save as Delta Table
        df.write.format("delta") \
            .mode("overwrite") \
            .save(f"Tables/UserEvents_{file_name}")

        print(f"✅ Saved: {file_name}")

# Run it
save_each_csv_as_delta()


# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

# Step 1: Read all monthly Delta Tables
delta_paths = [
    "Tables/UserEvents_2019_Oct",
    "Tables/UserEvents_2019_Nov",
    "Tables/UserEvents_2019_Dec",
    "Tables/UserEvents_2020_Jan",
    "Tables/UserEvents_2020_Feb"
]

df_all = None
for path in delta_paths:
    df_month = spark.read.format("delta").load(path)
    if df_all is None:
        df_all = df_month
    else:
        df_all = df_all.unionByName(df_month, allowMissingColumns=True)

# Step 2: Clean and add columns if needed
from pyspark.sql.functions import to_timestamp, to_date, current_date, col,date_format

df_all = df_all.withColumn("event_time", to_timestamp("event_time")) \
               .withColumn("event_date", to_date("event_time")) \
               .withColumn("price", col("price").cast("double")) \
               .withColumn("user_id", col("user_id").cast("string")) \
               .withColumn("product_id", col("product_id").cast("string")) \
               .withColumn("load_date", current_date())\
               .withColumn("month_name",date_format("event_date","MMMM"))
               

# Step 3: Save as final Fact Table
df_all.write.format("delta") \
    .mode("overwrite") \
    .save("Tables/Fact_UserEvents")

print("✅ Final Fact Table created: Fact_UserEvents")


# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

# Select distinct products
dim_product = df_all.select(
    "product_id", "brand", "category_id", "category_code"
).dropDuplicates(["product_id"])  

# Save as Delta Table
dim_product.write.format("delta") \
    .mode("overwrite") \
    .save("Tables/Dim_Product")




# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

dim_user = df_all.select("user_id", "user_session") \
                 .dropDuplicates(["user_id"]) 

dim_user.write.format("delta") \
    .mode("overwrite") \
    .save("Tables/Dim_User")




# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

from pyspark.sql.functions import year, month, dayofmonth, dayofweek

dim_date = df_all.select("event_date") \
                 .dropDuplicates(["event_date"]) \
                 .withColumn("year", year("event_date")) \
                 .withColumn("month", month("event_date")) \
                 .withColumn("day", dayofmonth("event_date")) \
                 .withColumn("day_of_week", dayofweek("event_date"))

dim_date.write.format("delta") \
    .mode("overwrite") \
    .save("Tables/Dim_Date")




# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

from pyspark.sql.functions import date_format

dim_date = dim_date.withColumn("month_name", date_format("event_date", "MMMM"))


# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

dim_date.write.format("delta") \
    .mode("overwrite") \
    .save("Tables/Dim_Date")


# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }
