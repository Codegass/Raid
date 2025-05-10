import os

def count_words(text):
    if not text:
        return 0
    return len(text.split())

if __name__ == "__main__":
    input_text = os.environ.get("INPUT_TEXT", "")
    word_count = count_words(input_text)
    print(f"The input text was: '{input_text}'")
    print(f"Word count: {word_count}") 