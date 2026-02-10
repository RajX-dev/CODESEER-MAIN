import os
import shutil

# ==========================================
# ⚙️ CONFIGURATION
# ==========================================
OLD_NAME = "codeseer"
NEW_NAME = "n3mo"

# Files that contain the word "codeseer" in strings or logic
FILES_TO_PATCH = [
    "setup.py",
    "docker-compose.yml",
    "MANIFEST.in",
    f"{OLD_NAME}/wrapper.py",
    f"{OLD_NAME}/src/cli.py",
    f"{OLD_NAME}/src/database.py"
]

def perform_surgery():
    print(f"🌊 Starting N3MO Transformation...")

    # 1. Update Content inside files
    for file_path in FILES_TO_PATCH:
        if os.path.exists(file_path):
            print(f"📝 Patching strings in: {file_path}")
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Replace lowercase, uppercase, and capitalized versions
            content = content.replace(OLD_NAME, NEW_NAME)
            content = content.replace(OLD_NAME.upper(), NEW_NAME.upper())
            content = content.replace(OLD_NAME.capitalize(), NEW_NAME.capitalize())
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
        else:
            print(f"⚠️  Skipping (File not found): {file_path}")

    # 2. Rename the actual folder
    if os.path.exists(OLD_NAME):
        print(f"📂 Renaming folder '{OLD_NAME}' -> '{NEW_NAME}'")
        try:
            # We use shutil.move to handle any cross-device issues
            shutil.move(OLD_NAME, NEW_NAME)
            print("✅ Folder rename successful.")
        except Exception as e:
            print(f"❌ Error renaming folder: {e}")
    else:
        print(f"ℹ️  Folder '{OLD_NAME}' already renamed or not found.")

    print(f"\n✨ Surgery Complete! Project is now N3MO.")
    print(f"👉 Next Step: Run 'pip install -e .' to activate the new command.")

if __name__ == "__main__":
    perform_surgery()