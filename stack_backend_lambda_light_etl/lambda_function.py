import re
import os
import json
import boto3
import awswrangler as wr
import concurrent.futures
from math import ceil


def lambda_handler(event, context):
    try:
        # Get s3_bucket and key from the S3 event
        s3_bucket = event['Records'][0]['s3']['bucket']['name']
        key = event['Records'][0]['s3']['object']['key']
        s3_path = f"s3://{s3_bucket}/{key}"

        # Define params for output. Reduce threads accordingly, dataset size vs Chunk Size, and output path (same bucket)
        num_rows_per_file = 10
        local_number_of_threads = 20

        # Knowledge Base Data Source location, coming from CDK Stack reading cdk.json
        # i.e. instead of hard-coding: datasets/demo_kb/knowledge-base-ecommerce-s3-001/v1
        output_s3_key = os.environ['KB_S3_ECOMM_PATH']
        
        # Read CSV directly into DataFrame using awswrangler
        print(f"Processing file from {s3_path}")
        df = wr.s3.read_csv(path=s3_path,  header=0, sep=',', quotechar='"')
        
        # Drop expected columns:
        df = df.drop(["customers_who_bought_this_item_also_bought", 
                    "items_customers_buy_after_viewing_this_item",
                    "customer_questions_and_answers",
                    "number_of_answered_questions",
                    "sellers",
                    "description"], axis=1)
        
        # Split the category and subcategories
        category_and_subcategories = df['amazon_category_and_sub_category'].str.split(' > ', expand=True)

        # Determine the number of subcategories
        num_subcategories = category_and_subcategories.shape[1]

        # Create the new columns
        col_name = f'subcategory_1'
        for i in range(num_subcategories):
            df[col_name] = category_and_subcategories[i]
            col_name = f'subcategory_{i+1}'

        # Assign the first column as the 'category'
        df['category'] = category_and_subcategories[0]

        # Drop column, after extracting values:
        df = df.drop(["amazon_category_and_sub_category"], axis=1)

        # If category and subcategory_1 are null, fill it with "others"
        df["category"] = df["category"].fillna("others")
        df["subcategory_1"] = df["subcategory_1"].fillna("others")

        # Leave only the Review rate, removing the "average_review_rating"
        df['average_review_rating'] = df['average_review_rating'].str.replace(' out of 5 stars', '')
        
        # Remove GBP symbol from price
        df['price'] = df['price'].str.replace('£', '')

        # Remove " new" from column "number_available_in_stock"
        df['number_available_in_stock'] = df['number_available_in_stock'].str.extract(r'(\d+)', expand=False)

        # There's a lot of garbage in some product_information values; e.g. "...Customer Reviews amznJQ.onReady(..."
        df['product_information'] = df['product_information'].str.slice(0, 100)
        df['product_information'] = df['product_information'].str.replace(r'amznJQ.*', '', regex=True)

        # Same for column "description", after a string> #productDescription
        df['product_description'] = df['product_description'].str.slice(0, 100)
        df['product_description'] = df['product_description'].str.replace(r'#productDescription*', '', regex=True)

        # As reviews can be quite long, we just get some of these:
        df['customer_reviews'] = df['customer_reviews'].str.slice(0, 100)

        # Rename column uniq_id for product_id
        df = df.rename(columns={'uniq_id': 'product_id'})

        print(f"Writing {len(df)} rows to Amazon S3...")

        with concurrent.futures.ThreadPoolExecutor(max_workers=local_number_of_threads) as executor:
            tasks = []
            for category, sub_category in df[['category', 'subcategory_1']].drop_duplicates().itertuples(index=False):
                task = (df, category, sub_category, s3_bucket, output_s3_key, num_rows_per_file)
                tasks.append(task)
    
            # Execute all tasks
            list(executor.map(write_csv_to_s3, tasks))  # Use list() to force execution

        return {
            "statusCode": 200,
            "body": {
                "message": f"Data successfully written to: {output_s3_key}",
                "rows_written": len(df)
            }
        }
        
    except Exception as e:
        print(f"Error processing file: {str(e)}")
        raise


def write_csv_to_s3(task):
    """_summary_

    Args:
        df (_type_): _description_
        args (_type_): _description_

    Returns:
        _type_: _description_
    """
    # S3 Client
    s3_client = boto3.client('s3')
    
    # Arguments
    df, category, sub_category, s3_bucket, s3_key, num_rows_per_file = task
    
    # Format names
    file_category = re.sub(r"[,\s&']", "_", category)
    file_subcategory = re.sub(r"[,\s&']", "_", sub_category)

    try:

        # Calculate the number of files needed
        subset = df[(df['category'] == category) & (df['subcategory_1'] == sub_category)]
        num_rows = len(subset)
        num_files = ceil(num_rows / num_rows_per_file)

        # Create the files
        for i in range(num_files):
            start_row = i * num_rows_per_file
            end_row = min((i + 1) * num_rows_per_file, num_rows)
            file_name = f"{file_category}_{file_subcategory}_{i+1}.csv"
            full_path_file_name = f"s3://{s3_bucket}/{s3_key}/{file_name}"

            # Write the CSV file
            # Optional, without WR: subset.iloc[start_row:end_row].to_csv(full_path_file_name, index=False)
            df_output = subset.iloc[start_row:end_row]
            wr.s3.to_csv(df_output, full_path_file_name, index=False)

            # Write Metadata Filter files
            file_metadata = {
                "metadataAttributes": {
                    "category" : category,
                    "subcategory_1" : sub_category,
                    "file_part" : i+1,
                    "total_files" : num_files
                }
            }
            
            # Metadata File
            s3_metadata_file = f"{s3_key}/{file_name}.metadata.json"

            # Write JSON metadata to S3. Do not return "response", as it's too much for logging/printing
            response = s3_client.put_object(Bucket=s3_bucket, Key=s3_metadata_file, Body=json.dumps(file_metadata))

        return None
    
    except Exception as e:
        print(f"Error while writing data: {e}")
        return None
    
