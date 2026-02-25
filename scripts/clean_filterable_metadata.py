import pandas as pd

# Columnas seguras para usar como metadatos filtrables (cortos)
FILTERABLE_COLUMNS = [
    'uniq_id',
    'product_name',
    'manufacturer',
    'price',
    'number_available_in_stock',
    'number_of_reviews',
    'number_of_answered_questions',
    'average_review_rating',
    'amazon_category_and_sub_category'
]


import os

INPUT_DIR = 'dataset'
OUTPUT_DIR = 'dataset-without-filter'


TRUNCATE_COLUMNS = [
    'description',
    'product_information',
    'product_description',
    'customer_questions_and_answers',
    'customer_reviews',
    'customers_who_bought_this_item_also_bought',
    'items_customers_buy_after_viewing_this_item',
    'sellers'
]

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    for filename in os.listdir(INPUT_DIR):
        if filename.endswith('.csv'):
            input_path = os.path.join(INPUT_DIR, filename)
            output_filterable = os.path.join(OUTPUT_DIR, filename.replace('.csv', '.csv'))
            output_full = os.path.join(OUTPUT_DIR, filename)
            df = pd.read_csv(input_path)

            # Truncar columnas extensas a 1024 caracteres si existen
            for col in TRUNCATE_COLUMNS:
                if col in df.columns:
                    df[col] = df[col].astype(str).str.slice(0, 1024)

            # Guardar solo columnas filtrables (acotadas)
            df[FILTERABLE_COLUMNS].to_csv(output_filterable, index=False)
            # Guardar todo el archivo original (con truncado)
            df.to_csv(output_full, index=False)
            print(f"Archivos generados para {filename}:\n- {output_filterable}\n- {output_full}")

if __name__ == "__main__":
    main()
