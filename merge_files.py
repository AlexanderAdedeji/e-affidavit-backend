import os
from pathlib import Path

def find_files_with_extension(base_dir, extensions):
    """
    Recursively find all files with the given extensions in the base directory.
    """
    base_path = Path(base_dir)
    return [file for file in base_path.rglob('*') if file.suffix in extensions]

def merge_files(base_dir, output_file, extensions=(".py",)):
    """
    Merge the content of all files with the specified extensions into one file.
    """
    try:
        # Find all matching files
        files = find_files_with_extension(base_dir, extensions)
        print(f"Found {len(files)} files with extensions {extensions}. Merging...")

        # Combine the content
        with open(output_file, "w", encoding="utf-8") as out_file:
            for file in files:
                with open(file, "r", encoding="utf-8") as in_file:
                    out_file.write(f"\n# ===== File: {file} =====\n")
                    out_file.write(in_file.read())
                    out_file.write("\n")

        print(f"All files successfully merged into {output_file}")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    # Define the directory to scan and output file
    base_directory = Path(__file__).parent  # Current directory
    output_file_path = base_directory / "merged-python-files.txt"

    # Define file extensions to include
    file_extensions = (".py", ".sql", ".ini")  # Include Alembic's .ini or .sql if needed

    # Run the merging process
    merge_files(base_directory, output_file_path, file_extensions)
