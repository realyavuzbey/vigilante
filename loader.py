import subprocess
import time
import os

def run(cmd):
    print(f"\n📦 Running: {cmd}")
    result = subprocess.run(cmd, shell=True)
    if result.returncode != 0:
        print("❌ Error occurred.")
        exit(1)

def github_push():
    run("git add .")
    run("git commit -m 'Auto push from loader'")
    run("git push origin main")

def build_and_upload_pypi():
    run("rm -rf dist/ build/ *.egg-info")
    run("python setup.py sdist bdist_wheel")
    run("twine upload dist/*")

def main():
    print("🚀 Starting Vigilante Deployment...\n")
    github_push()
    time.sleep(2)
    build_and_upload_pypi()
    print("\n✅ ALL DONE!")

if __name__ == "__main__":
    main()