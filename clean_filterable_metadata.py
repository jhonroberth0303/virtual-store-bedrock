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

INPUT_FILE = 'dataset/sample_raw_productos_por_categoria_10_total_1343_productos.csv'
OUTPUT_FILTERABLE = 'dataset/sample_productos_filterable_metadata.csv'
OUTPUT_FULL = 'dataset/sample_productos_full.csv'

def main():
    df = pd.read_csv(INPUT_FILE)
    # Guardar solo columnas filtrables
    df[FILTERABLE_COLUMNS].to_csv(OUTPUT_FILTERABLE, index=False)
    # Guardar todo el archivo original (por si necesitas el full para embeddings)
    df.to_csv(OUTPUT_FULL, index=False)
    print(f"Archivos generados:\n- {OUTPUT_FILTERABLE}\n- {OUTPUT_FULL}")

if __name__ == "__main__":
    main()
