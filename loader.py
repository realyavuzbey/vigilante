import subprocess
import time
import os
import sys

def run(cmd, critical=True):
    print(f"\n[RUNNING] {cmd}")
    result = subprocess.run(cmd, shell=True)
    if result.returncode != 0:
        print("[ERROR] Command failed.")
        if critical:
            sys.exit(1)

def check_git_repo():
    if not os.path.isdir(".git"):
        print("[ERROR] Not a Git repo. Run 'git init' and set remote.")
        sys.exit(1)

def github_push():
    run("git add .")
    run('git commit -m "auto: loader push"')
    run("git push origin main")

def clean_build_artifacts():
    run("rm -rf dist/ build/ *.egg-info", critical=False)

def build_package():
    run("python setup.py sdist bdist_wheel")

def upload_to_pypi():
    run("twine upload dist/*")

def main():
    print("=== VIGILANTE DEPLOY ===")
    check_git_repo()
    github_push()
    clean_build_artifacts()
    build_package()
    time.sleep(1)
    upload_to_pypi()
    print("\n[OK] Deployment complete.")

if __name__ == "__main__":
    main()
