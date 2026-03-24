import sys

filepath = r'c:\Users\varun\Downloads\AI interview (3)\AI interview\Ai interview\futurproctor\proctoring\templates\round1_exam.html'

with open(filepath, 'rb') as f:
    raw = f.read(100)
    print("Raw leading bytes:", raw[:20])

try:
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    print("Read as UTF-8.")
except Exception as e:
    print("Failed to read as UTF-8:", e)
    try:
        with open(filepath, 'r', encoding='utf-16') as f:
            content = f.read()
        print("Read as UTF-16.")
    except Exception as e2:
        print("Failed to read as UTF-16:", e2)
        sys.exit(1)

new_content = content.replace("{{ mcqs| length |default: 0 }}", "{{ mcqs|length|default:0 }}")
if new_content == content:
    print("Replace had no effect. Did not find target string.")
else:
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print("Replaced string and saved as UTF-8.")
