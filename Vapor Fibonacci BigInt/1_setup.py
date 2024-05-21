import os
import time
import shutil
import urllib.request
import tarfile

# Download zip again if it is older than X minutes.
GITHUB_MAX_ZIP_AGE_MINUTES = 15


def download_zip(url: str, local_path: str):
    if os.path.exists(local_path):
        mtime = os.path.getmtime(local_path)
        now = time.time()
        assert now >= mtime, f"'{local_path}' created in the future?"

        age_minutes = (now - mtime) / 60
        m = int(age_minutes)

        if age_minutes <= GITHUB_MAX_ZIP_AGE_MINUTES:
            print(f"  use {local_path} (downloaded {m} min ago)")
            return

        print(f"  rm {local_path} (too old, downloaded {m} min ago)")

        try:
            os.remove(local_path)
        except FileNotFoundError:
            pass

    print(f"  download {url} -> {local_path}")
    urllib.request.urlretrieve(url, local_path)


def unzip(zip_path: str, dir: str):
    print(f"  unzip {zip_path} -> {dir}")

    if zip_path.endswith("tar.xz"):
        os.system(f'tar --extract --xz -f "{zip_path}" --directory="{dir}"')
        return

    shutil.unpack_archive(zip_path, dir)


def rmtree(dir_path: str):
    try:
        print(f"  rm -r {dir_path}")
        shutil.rmtree(dir_path)
    except FileNotFoundError:
        pass


def move_dir(src_dir: str, dst_dir: str):
    rmtree(dst_dir)
    print(f"  mv {src_dir} -> {dst_dir}")
    shutil.move(src_dir, dst_dir)


def main():
    print("Attaswift")
    url = "https://github.com/attaswift/BigInt/archive/refs/heads/master.zip"
    zip_path = "Zip/BigInt-master.zip"
    dir_path = "Zip/BigInt-master"
    download_zip(url, zip_path)
    unzip(zip_path, "Zip")
    move_dir(f"{dir_path}/Sources", "Sources/Attaswift")
    rmtree(dir_path)

    print("Violet-BigInt-XsProMax")
    url = "https://github.com/LiarPrincess/Violet-BigInt-XsProMax/archive/refs/heads/main.zip"
    zip_path = "Zip/Violet-BigInt-XsProMax-main.zip"
    dir_path = "Zip/Violet-BigInt-XsProMax-main"
    download_zip(url, zip_path)
    unzip(zip_path, "Zip")
    move_dir(f"{dir_path}/Sources", "Sources/Violet")
    rmtree(dir_path)

    print("Numberick")
    url = "https://github.com/oscbyspro/Numberick/archive/refs/heads/main.zip"
    zip_path = "Zip/Numberick-main.zip"
    dir_path = "Zip/Numberick-main"
    download_zip(url, zip_path)
    unzip(zip_path, "Zip")
    move_dir(f"{dir_path}/Sources/NBKCoreKit", "Sources/NumberickCore")
    move_dir(f"{dir_path}/Sources/NBKFlexibleWidthKit", "Sources/Numberick")
    rmtree(dir_path)

    print("GMP")
    url = "https://gmplib.org/download/gmp/gmp-6.3.0.tar.xz"
    zip_path = "Zip/gmp.tar.xz"
    download_zip(url, zip_path)
    try:
        unzip(zip_path, "Zip")
        move_dir("Zip/gmp-6.3.0", "gmp")
    except:
        print(f"  ERROR: Unable to extract '{zip_path}'")


if __name__ == "__main__":
    main()
