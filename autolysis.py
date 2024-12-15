# /// script
# requires-python = ">=3.9"
# dependencies = [
#   "pandas",
#   "seaborn",
#   "matplotlib",
#   "numpy",
#   "scipy",
#   "openai",
#   "scikit-learn",
#   "requests",
#   "ipykernel",  # Added ipykernel
# ]
# ///  # Closing tag

import os
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import requests
import sys
import logging
from datetime import datetime

# Configure Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Global Constants
API_PROXY_TOKEN = os.getenv("AIPROXY_TOKEN", None)
API_PROXY_BASE_URL = "https://aiproxy.sanand.workers.dev/openai/v1"

if not API_PROXY_TOKEN:
    logging.error("API Proxy Token not found in environment variables.")
    sys.exit(1)

# Utility Functions
def read_csv(filename):
    """Read the CSV file and return a DataFrame."""
    try:
        df = pd.read_csv(filename, encoding="utf-8")
        logging.info(f"Dataset loaded successfully: {filename}")
        return df
    except UnicodeDecodeError:
        logging.warning(f"Encoding issue detected with {filename}. Trying 'latin1'.")
        try:
            return pd.read_csv(filename, encoding="latin1")
        except Exception as e:
            logging.error(f"Failed to load {filename} with fallback encoding: {e}")
            sys.exit(1)
    except Exception as e:
        logging.error(f"Error loading {filename}: {e}")
        sys.exit(1)

def analyze_data(df):
    """Perform basic analysis on the dataset."""
    try:
        analysis = {
            "shape": df.shape,
            "columns": df.columns.tolist(),
            "missing_values": df.isnull().sum().to_dict(),
            "summary_statistics": df.describe(include="all").to_dict()
        }
        logging.info("Dataset analysis completed.")
        return analysis
    except Exception as e:
        logging.error(f"Error analyzing dataset: {e}")
        sys.exit(1)

def create_output_folder(output_folder):
    """Create an output folder if it doesn't exist."""
    try:
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)
            logging.info(f"Output folder created: {output_folder}")
    except Exception as e:
        logging.error(f"Error creating output folder: {e}")
        sys.exit(1)

# Visualization Functions
def visualize_data(df, output_folder, output_prefix):
    """Generate visualizations for the dataset and save them in the output folder."""
    charts = []
    numeric_columns = df.select_dtypes(include=["number"]).columns

    if len(numeric_columns) > 0:
        try:
            plt.figure(figsize=(14, 12))
            heatmap = sns.heatmap(
                df[numeric_columns].corr(),
                annot=True,
                cmap="coolwarm",
                fmt=".2f",
                cbar_kws={'shrink': 0.8}
            )
            heatmap.set_title("Correlation Heatmap", fontsize=16, pad=20)
            plt.tight_layout()
            heatmap_file = os.path.join(output_folder, f"{output_prefix}_heatmap.png")
            plt.savefig(heatmap_file, dpi=300)
            charts.append(heatmap_file)
            logging.info("Heatmap generated.")
            plt.close()
        except Exception as e:
            logging.warning(f"Error generating heatmap: {e}")
    else:
        logging.info("No numeric columns available for heatmap.")

    # Histogram for numeric columns
    for column in numeric_columns:
        try:
            plt.figure(figsize=(10, 6))
            sns.histplot(df[column].dropna(), kde=True, bins=30, color="blue")
            plt.title(f"Distribution of {column}", fontsize=16)
            plt.xlabel(column, fontsize=14)
            plt.ylabel("Frequency", fontsize=14)
            plt.tight_layout()
            histogram_file = os.path.join(output_folder, f"{output_prefix}_{column}_histogram.png")
            plt.savefig(histogram_file, dpi=300)
            charts.append(histogram_file)
            logging.info(f"Histogram for {column} generated.")
            plt.close()
        except Exception as e:
            logging.warning(f"Error generating histogram for {column}: {e}")

    # Barplot for categorical columns
    barplot_column = ask_chatgpt_for_barplot_column(df, output_prefix)
    if barplot_column and barplot_column in df.columns:
        try:
            barplot_file = generate_barplot(df, barplot_column, output_folder, output_prefix)
            charts.append(barplot_file)
        except Exception as e:
            logging.warning(f"Error generating barplot for {barplot_column}: {e}")
    else:
        logging.info(f"No valid column found for barplot: {barplot_column}")

    return charts

def generate_barplot(df, barplot_column, output_folder, output_prefix):
    """Generate a bar plot for the specified column (Top 10 items)."""
    plt.figure(figsize=(14, 8))
    top_categories = df[barplot_column].value_counts().head(10)
    top_categories.sort_values().plot(kind="barh", color="skyblue")
    plt.title(f"Top 10 {barplot_column} Categories", fontsize=16, pad=20)
    plt.xlabel("Frequency", fontsize=14, labelpad=15)
    plt.ylabel(barplot_column, fontsize=14, labelpad=15)
    plt.tight_layout(pad=3.0)
    barplot_file = os.path.join(output_folder, f"{output_prefix}_{barplot_column}_barplot.png")
    plt.savefig(barplot_file, dpi=300)
    plt.close()
    logging.info(f"Barplot for {barplot_column} generated.")
    return barplot_file

# LLM Interaction Functions
def ask_chatgpt_for_barplot_column(df, filename):
    """Ask ChatGPT to suggest a column name from the dataset."""
    columns_list = ", ".join(df.columns)
    summary_prompt = f"""Dataset loaded: {filename}\nColumns: {columns_list}\nSuggest a single categorical column name suitable for a bar plot."""
    return send_to_gpt(summary_prompt)

def send_to_gpt(prompt):
    """Send a prompt to GPT and return the response."""
    url = f"{API_PROXY_BASE_URL}/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_PROXY_TOKEN}"
    }
    data = {
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7
    }

    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        result = response.json()
        return result["choices"][0]["message"]["content"].strip()
    except requests.exceptions.RequestException as e:
        logging.error(f"Error communicating with GPT: {e}")
        return None

def narrate_story(analysis, charts, filename):
    """Use GPT to narrate a story about the analysis."""
    summary_prompt = f"""I analyzed a dataset from {filename}. Details:\n- Shape: {analysis['shape']}\n- Columns: {analysis['columns']}\n- Missing Values: {analysis['missing_values']}\n- Summary Statistics: {analysis['summary_statistics']}\nWrite a short summary and recommendations."""
    return send_to_gpt(summary_prompt)

# Markdown and File Management
def save_markdown(story, charts, output_folder):
    """Save the narrated story and chart references to a README.md file."""
    readme_file = os.path.join(output_folder, "README.md")
    with open(readme_file, "w") as f:
        f.write("# Analysis Report\n\n")
        f.write(story + "\n\n")
        for chart in charts:
            f.write(f"![Chart](./{os.path.basename(chart)})\n")
    logging.info(f"README.md saved in {output_folder}")

# Main Function
def main():
    if len(sys.argv) < 2 or len(sys.argv) > 3:
        print("Usage: python autolysis.py dataset.csv [output_directory]")
        return

    dataset_path = sys.argv[1]
    output_folder = sys.argv[2] if len(sys.argv) == 3 else os.path.splitext(dataset_path)[0]

    if not os.path.isfile(dataset_path):
        logging.error(f"Error: File '{dataset_path}' not found.")
        return

    create_output_folder(output_folder)

    df = read_csv(dataset_path)
    analysis = analyze_data(df)
    charts = visualize_data(df, output_folder, os.path.basename(dataset_path).split('.')[0])
    story = narrate_story(analysis, charts, dataset_path)
    save_markdown(story, charts, output_folder)
    logging.info(f"All outputs saved in {output_folder}")

if __name__ == "__main__":
    main()
