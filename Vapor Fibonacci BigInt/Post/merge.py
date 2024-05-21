import os

ROOT_DIR = "."
OUTPUT_PATH = "Readme.md"


def main():
    with open(OUTPUT_PATH, "w") as f:
        dir_path = os.path.join(ROOT_DIR, ROOT_DIR)
        entries = os.listdir(dir_path)

        for entry in sorted(entries):
            if entry.endswith("md") and entry != "Readme.md":
                file_content: str = ""
                file_path = os.path.join(dir_path, entry)

                with open(file_path, "r") as f_in:
                    file_content = f_in.read()

                assert file_content, "Empty: " + file_path
                f.write(file_content)
                f.write("\n")

        f.write("\n")


if __name__ == "__main__":
    main()
