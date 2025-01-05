import streamlit as st

def main():
    # Set global page configuration
    st.set_page_config(page_title="Tournalytics", page_icon="🎮", layout="wide")

    # Welcome message (optional)
    st.title("🎮 Welcome to Tournalytics 🎮")
    st.subheader("Navigate to the desired section using the menu above.")

if __name__ == "__main__":
    main()
