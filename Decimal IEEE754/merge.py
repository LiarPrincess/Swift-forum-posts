import os

ROOT_DIR = "."
OUTPUT_PATH = "Readme.md"


def main():
    dir_names: list[str] = []

    for entry in os.listdir(ROOT_DIR):
        if os.path.isdir(entry):
            dir_names.append(entry)

    dir_names.sort()

    with open(OUTPUT_PATH, "w") as f:
        for dir_name in dir_names:
            if dir_name != "1_start":
                section_name = dir_name[2:]
                section_name = section_name.replace("_", " ")
                section_name = section_name.title()

                f.write("# ")
                f.write(section_name)
                f.write("\n\n")

            dir_path = os.path.join(ROOT_DIR, dir_name)
            entries = os.listdir(dir_path)

            for entry in sorted(entries):
                if not entry.endswith("md"):
                    continue

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
