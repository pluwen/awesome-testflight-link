#!/usr/bin/python
from utils import renew_readme, load_links

def main():
    load_links()
    print("[info] Regenerating README...")
    renew_readme()
    print("[info] Done!")
if __name__ == "__main__":
    main()
